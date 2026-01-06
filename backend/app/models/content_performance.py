"""
ContentPerformance model - tracks performance metrics of published content over time.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.generated_content import GeneratedContent


class ContentPerformance(Base):
    """
    ContentPerformance model for tracking published content metrics.

    Stores periodic snapshots of Reddit metrics for performance analysis.
    Multiple snapshots per content allow tracking performance over time.
    """

    __tablename__ = "content_performances"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # Foreign key to content
    content_id: Mapped[int] = Column(
        Integer,
        ForeignKey("generated_contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Snapshot timestamp
    snapshot_at: Mapped[datetime] = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    # Core metrics
    score: Mapped[int] = Column(Integer, default=0, nullable=False)
    upvotes: Mapped[int] = Column(Integer, default=0, nullable=False)
    downvotes: Mapped[int] = Column(Integer, default=0, nullable=False)
    num_replies: Mapped[int] = Column(Integer, default=0, nullable=False)

    # Calculated metrics
    engagement_rate: Mapped[Optional[float]] = Column(Float, nullable=True)
    velocity: Mapped[Optional[float]] = Column(Float, nullable=True)  # Score change rate

    # Content status
    is_removed: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    removal_reason: Mapped[Optional[str]] = Column(String(255), nullable=True)

    # Reddit awards (if any)
    awards: Mapped[Optional[dict]] = Column(JSON, nullable=True)

    # Extended platform-specific metrics
    platform_metrics: Mapped[dict] = Column(JSON, default=dict, nullable=False)
    # Stores: controversiality, depth, parent_score, subreddit_subscribers, etc.

    # Relationships
    content: Mapped["GeneratedContent"] = relationship(
        "GeneratedContent",
        back_populates="performance_snapshots"
    )

    # Indexes
    __table_args__ = (
        Index('idx_perf_content_snapshot', 'content_id', 'snapshot_at'),
    )

    def __repr__(self) -> str:
        return f"<ContentPerformance(id={self.id}, content_id={self.content_id}, score={self.score})>"

    @property
    def net_votes(self) -> int:
        """Calculate net votes (upvotes - downvotes)."""
        return self.upvotes - self.downvotes

    @property
    def is_successful(self) -> bool:
        """
        Determine if content is successful based on metrics.
        Threshold: score >= 10 and not removed
        """
        return self.score >= 10 and not self.is_removed and not self.is_deleted
