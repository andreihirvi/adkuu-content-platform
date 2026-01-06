"""
Opportunity model - represents a Reddit post that's a potential advertising opportunity.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped
import enum

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.generated_content import GeneratedContent


class OpportunityStatus(str, enum.Enum):
    """Status of an opportunity in the pipeline."""
    PENDING = "pending"           # Discovered, awaiting review
    APPROVED = "approved"         # Approved for content generation
    REJECTED = "rejected"         # Rejected by user
    GENERATING = "generating"     # Content being generated
    READY = "ready"              # Content ready for review
    PUBLISHING = "publishing"     # Being published
    PUBLISHED = "published"       # Successfully published
    EXPIRED = "expired"          # Too old to act on
    FAILED = "failed"            # Failed to publish


class OpportunityUrgency(str, enum.Enum):
    """Urgency level based on timing analysis."""
    URGENT = "urgent"    # Act within 30 min
    HIGH = "high"        # Act within 2 hours
    MEDIUM = "medium"    # Act within 4 hours
    LOW = "low"          # Can wait longer
    EXPIRED = "expired"  # Too late


class Opportunity(Base):
    """
    Opportunity model representing a Reddit post that's a potential advertising opportunity.

    Contains:
    - Reddit post metadata
    - Scoring information (relevance, virality, timing)
    - Pipeline status
    """

    __tablename__ = "opportunities"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # Foreign key to project
    project_id: Mapped[int] = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Reddit post identification
    reddit_post_id: Mapped[str] = Column(String(50), unique=True, nullable=False, index=True)
    subreddit: Mapped[str] = Column(String(100), nullable=False, index=True)

    # Post content
    post_title: Mapped[str] = Column(Text, nullable=False)
    post_content: Mapped[Optional[str]] = Column(Text, nullable=True)
    post_url: Mapped[str] = Column(String(500), nullable=False)
    post_author: Mapped[Optional[str]] = Column(String(100), nullable=True)

    # Post metrics at discovery time
    post_created_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    post_score: Mapped[int] = Column(Integer, default=0, nullable=False)
    post_num_comments: Mapped[int] = Column(Integer, default=0, nullable=False)
    post_upvote_ratio: Mapped[Optional[float]] = Column(Float, nullable=True)

    # Scoring
    relevance_score: Mapped[Optional[float]] = Column(Float, nullable=True)  # 0-1
    virality_score: Mapped[Optional[float]] = Column(Float, nullable=True)   # 0-1
    timing_score: Mapped[Optional[float]] = Column(Float, nullable=True)     # 0-1
    composite_score: Mapped[Optional[float]] = Column(Float, nullable=True)  # 0-1

    # Urgency classification
    urgency: Mapped[Optional[str]] = Column(String(20), nullable=True)

    # Velocity metrics (for timing analysis)
    velocity: Mapped[Optional[float]] = Column(Float, nullable=True)
    velocity_threshold: Mapped[Optional[float]] = Column(Float, nullable=True)

    # Status tracking
    status: Mapped[str] = Column(
        String(50),
        default=OpportunityStatus.PENDING.value,
        nullable=False,
        index=True
    )

    # Expiration (when opportunity becomes stale)
    expires_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    # Timestamps
    discovered_at: Mapped[datetime] = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    processed_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    # Additional metadata (flexible storage)
    opportunity_metadata: Mapped[dict] = Column(JSON, default=dict, nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="opportunities")
    generated_contents: Mapped[List["GeneratedContent"]] = relationship(
        "GeneratedContent",
        back_populates="opportunity",
        cascade="all, delete-orphan"
    )

    # Indexes for common queries
    __table_args__ = (
        Index('idx_opp_project_status', 'project_id', 'status'),
        Index('idx_opp_composite_desc', composite_score.desc()),
        Index('idx_opp_discovered', 'discovered_at'),
    )

    def __repr__(self) -> str:
        return f"<Opportunity(id={self.id}, reddit_id='{self.reddit_post_id}', status='{self.status}')>"

    @property
    def age_hours(self) -> float:
        """Calculate age of post in hours."""
        if self.post_created_at:
            delta = datetime.utcnow() - self.post_created_at
            return delta.total_seconds() / 3600
        return 0.0

    @property
    def is_expired(self) -> bool:
        """Check if opportunity has expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        # Default: expire after 24 hours
        return self.age_hours > 24
