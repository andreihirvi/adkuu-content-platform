"""
SubredditConfig model - stores configuration and metadata for target subreddits.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project


class SubredditConfig(Base):
    """
    SubredditConfig model for storing subreddit-specific configuration.

    Contains:
    - Subreddit metadata (subscribers, activity)
    - Posting requirements (min karma, account age)
    - Performance history
    - Optimal posting times
    """

    __tablename__ = "subreddit_configs"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # Foreign key to project
    project_id: Mapped[int] = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Subreddit identification
    subreddit_name: Mapped[str] = Column(String(100), nullable=False, index=True)

    # Subreddit metadata
    subscribers: Mapped[Optional[int]] = Column(Integer, nullable=True)
    active_users: Mapped[Optional[int]] = Column(Integer, nullable=True)
    posts_per_day: Mapped[Optional[float]] = Column(Float, nullable=True)
    subreddit_type: Mapped[Optional[str]] = Column(String(50), nullable=True)  # public, restricted, private

    # Posting requirements
    min_account_age_days: Mapped[Optional[int]] = Column(Integer, nullable=True)
    min_karma: Mapped[Optional[int]] = Column(Integer, nullable=True)
    min_comment_karma: Mapped[Optional[int]] = Column(Integer, nullable=True)
    allowed_content_types: Mapped[Optional[list]] = Column(JSON, nullable=True)  # ['text', 'link', 'image']

    # Rules and guidelines
    posting_rules: Mapped[Optional[str]] = Column(Text, nullable=True)
    rules_summary: Mapped[Optional[str]] = Column(Text, nullable=True)

    # Performance history
    avg_post_score: Mapped[Optional[float]] = Column(Float, nullable=True)
    avg_comment_score: Mapped[Optional[float]] = Column(Float, nullable=True)
    our_avg_score: Mapped[Optional[float]] = Column(Float, nullable=True)  # Our content's avg score
    our_removal_rate: Mapped[Optional[float]] = Column(Float, nullable=True)

    # Optimal timing
    best_posting_hours: Mapped[Optional[list]] = Column(JSON, nullable=True)  # List of UTC hours
    best_posting_days: Mapped[Optional[list]] = Column(JSON, nullable=True)   # List of weekday numbers

    # Velocity thresholds (for rising post detection)
    velocity_threshold: Mapped[Optional[float]] = Column(Float, nullable=True)

    # Status
    is_enabled: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    last_analyzed_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    last_mined_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    # Additional configuration
    config_metadata: Mapped[dict] = Column(JSON, default=dict, nullable=False)

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
    project: Mapped["Project"] = relationship("Project", back_populates="subreddit_configs")

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('project_id', 'subreddit_name', name='uq_project_subreddit'),
    )

    def __repr__(self) -> str:
        return f"<SubredditConfig(id={self.id}, subreddit='{self.subreddit_name}')>"

    @property
    def size_category(self) -> str:
        """Categorize subreddit by size."""
        if not self.subscribers:
            return "unknown"
        elif self.subscribers < 50000:
            return "small"
        elif self.subscribers < 500000:
            return "medium"
        elif self.subscribers < 2000000:
            return "large"
        else:
            return "massive"

    def get_velocity_threshold(self) -> float:
        """Get velocity threshold based on subreddit size."""
        if self.velocity_threshold:
            return self.velocity_threshold

        # Default thresholds by size
        thresholds = {
            "small": 5.0,
            "medium": 15.0,
            "large": 50.0,
            "massive": 200.0,
            "unknown": 15.0
        }
        return thresholds.get(self.size_category, 15.0)
