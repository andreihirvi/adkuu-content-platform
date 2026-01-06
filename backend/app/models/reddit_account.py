"""
RedditAccount model - manages Reddit accounts for multi-account publishing.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped
import enum

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.generated_content import GeneratedContent


class AccountStatus(str, enum.Enum):
    """Status of a Reddit account."""
    ACTIVE = "active"               # Ready to use
    RATE_LIMITED = "rate_limited"   # Temporarily rate limited
    SUSPENDED = "suspended"         # Account suspended by Reddit
    OAUTH_EXPIRED = "oauth_expired" # OAuth token expired, needs refresh
    INACTIVE = "inactive"           # Manually deactivated


class RedditAccount(Base):
    """
    RedditAccount model for managing Reddit accounts.

    Supports:
    - OAuth2 authentication with encrypted tokens
    - Account health monitoring
    - Rate limiting per account
    - Account selection scoring
    """

    __tablename__ = "reddit_accounts"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # Foreign key to project
    project_id: Mapped[Optional[int]] = Column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Account identification
    username: Mapped[str] = Column(String(100), nullable=False, index=True)
    display_name: Mapped[Optional[str]] = Column(String(100), nullable=True)

    # OAuth credentials (encrypted)
    access_token_encrypted: Mapped[Optional[str]] = Column(Text, nullable=True)
    refresh_token_encrypted: Mapped[Optional[str]] = Column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    oauth_scopes: Mapped[Optional[List]] = Column(JSON, nullable=True)

    # Reddit app credentials (for this account)
    client_id: Mapped[Optional[str]] = Column(String(100), nullable=True)
    client_secret_encrypted: Mapped[Optional[str]] = Column(Text, nullable=True)
    user_agent: Mapped[Optional[str]] = Column(String(255), nullable=True)

    # Account metrics (for selection scoring)
    karma_total: Mapped[int] = Column(Integer, default=0, nullable=False)
    karma_comment: Mapped[int] = Column(Integer, default=0, nullable=False)
    karma_post: Mapped[int] = Column(Integer, default=0, nullable=False)
    account_age_days: Mapped[Optional[int]] = Column(Integer, nullable=True)
    account_created_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    # Rate limiting
    last_action_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    daily_actions_count: Mapped[int] = Column(Integer, default=0, nullable=False)
    daily_actions_reset_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    # Health metrics
    status: Mapped[str] = Column(
        String(50),
        default=AccountStatus.ACTIVE.value,
        nullable=False,
        index=True
    )
    health_score: Mapped[float] = Column(Float, default=1.0, nullable=False)
    last_health_check_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    consecutive_failures: Mapped[int] = Column(Integer, default=0, nullable=False)

    # Performance tracking
    total_posts_made: Mapped[int] = Column(Integer, default=0, nullable=False)
    total_posts_removed: Mapped[int] = Column(Integer, default=0, nullable=False)
    removal_rate: Mapped[float] = Column(Float, default=0.0, nullable=False)

    # Subreddit activity tracking (for selection)
    subreddit_activity: Mapped[dict] = Column(JSON, default=dict, nullable=False)
    # Structure: {"subreddit_name": {"posts": N, "karma": N, "last_activity": timestamp}}

    # Additional metadata
    account_metadata: Mapped[dict] = Column(JSON, default=dict, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="reddit_accounts",
        foreign_keys=[project_id]
    )
    generated_contents: Mapped[List["GeneratedContent"]] = relationship(
        "GeneratedContent",
        back_populates="reddit_account"
    )

    def __repr__(self) -> str:
        return f"<RedditAccount(id={self.id}, username='{self.username}', status='{self.status}')>"

    @property
    def is_active(self) -> bool:
        """Check if account is active and usable."""
        return self.status == AccountStatus.ACTIVE.value

    @property
    def can_post(self) -> bool:
        """Check if account can make a post right now."""
        from app.core.config import settings

        if not self.is_active:
            return False

        # Check daily limit
        if self.daily_actions_count >= settings.MAX_DAILY_POSTS_PER_ACCOUNT:
            return False

        # Check minimum interval
        if self.last_action_at:
            seconds_since_last = (datetime.utcnow() - self.last_action_at).total_seconds()
            if seconds_since_last < settings.REDDIT_MIN_ACTION_INTERVAL_SECONDS:
                return False

        return True

    @property
    def selection_score(self) -> float:
        """
        Calculate account selection score for choosing best account.

        Higher score = better account for posting.
        """
        score = 100.0

        # Karma bonus (up to +20)
        score += min(self.karma_comment / 1000, 20)

        # Age bonus (up to +10)
        if self.account_age_days:
            score += min(self.account_age_days / 30, 10)

        # Low removal rate bonus
        if self.removal_rate < 0.05:
            score += 10
        elif self.removal_rate > 0.20:
            score -= 20

        # Health score modifier
        score *= self.health_score

        # Penalize if close to daily limit
        from app.core.config import settings
        remaining = settings.MAX_DAILY_POSTS_PER_ACCOUNT - self.daily_actions_count
        if remaining <= 2:
            score -= 10

        return max(0, score)
