"""
LearningFeature model - stores aggregated learning data for ML and optimization.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project


class FeatureType(str):
    """Types of learning features."""
    SUBREDDIT = "subreddit"           # Per-subreddit performance
    KEYWORD = "keyword"               # Per-keyword effectiveness
    TIMING = "timing"                 # Timing patterns (hour/day)
    CONTENT_PATTERN = "content_pattern"  # Content style effectiveness
    AUTHOR = "author"                 # Author/account performance
    TOPIC = "topic"                   # Topic cluster performance


class LearningFeature(Base):
    """
    LearningFeature model for storing aggregated learning data.

    Used for:
    - ML model training
    - Content optimization
    - Performance prediction
    - A/B testing results
    """

    __tablename__ = "learning_features"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # Feature identification
    feature_type: Mapped[str] = Column(String(50), nullable=False, index=True)
    feature_key: Mapped[str] = Column(String(255), nullable=False, index=True)

    # Optional project scope (None = global)
    project_id: Mapped[Optional[int]] = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Aggregated metrics
    sample_count: Mapped[int] = Column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = Column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = Column(Integer, default=0, nullable=False)

    # Performance metrics
    success_rate: Mapped[Optional[float]] = Column(Float, nullable=True)
    avg_score: Mapped[Optional[float]] = Column(Float, nullable=True)
    avg_engagement: Mapped[Optional[float]] = Column(Float, nullable=True)
    avg_removal_rate: Mapped[Optional[float]] = Column(Float, nullable=True)

    # Statistical data
    score_stddev: Mapped[Optional[float]] = Column(Float, nullable=True)
    confidence: Mapped[Optional[float]] = Column(Float, nullable=True)

    # Feature-specific detailed data
    feature_data: Mapped[dict] = Column(JSON, default=dict, nullable=False)
    # Structure depends on feature_type:
    # - subreddit: {"best_hours": [...], "best_days": [...], "topic_affinity": {...}}
    # - keyword: {"contexts": [...], "avg_relevance": float}
    # - timing: {"hour_performance": {...}, "day_performance": {...}}
    # - content_pattern: {"style_performance": {...}, "length_correlation": float}

    # Thompson Sampling bandit state (for multi-armed bandit optimization)
    bandit_alpha: Mapped[float] = Column(Float, default=1.0, nullable=False)  # Successes + 1
    bandit_beta: Mapped[float] = Column(Float, default=1.0, nullable=False)   # Failures + 1

    # Time-based decay
    decay_factor: Mapped[float] = Column(Float, default=1.0, nullable=False)
    last_decay_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    # Timestamps
    last_updated_at: Mapped[datetime] = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    created_at: Mapped[datetime] = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project")

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('feature_type', 'feature_key', 'project_id', name='uq_feature_type_key_project'),
    )

    def __repr__(self) -> str:
        return f"<LearningFeature(type='{self.feature_type}', key='{self.feature_key}')>"

    def update_success_rate(self) -> None:
        """Recalculate success rate from counts."""
        total = self.success_count + self.failure_count
        if total > 0:
            self.success_rate = self.success_count / total
        else:
            self.success_rate = None

    def record_outcome(self, success: bool, score: float = None) -> None:
        """
        Record an outcome for this feature.

        Args:
            success: Whether the content was successful
            score: Optional score for the content
        """
        self.sample_count += 1

        if success:
            self.success_count += 1
            self.bandit_alpha += 1
        else:
            self.failure_count += 1
            self.bandit_beta += 1

        self.update_success_rate()

        # Update rolling average score
        if score is not None and self.avg_score is not None:
            # Exponential moving average
            alpha = 0.1  # Smoothing factor
            self.avg_score = alpha * score + (1 - alpha) * self.avg_score
        elif score is not None:
            self.avg_score = score

    def get_thompson_sample(self) -> float:
        """
        Get a Thompson Sampling sample for bandit optimization.

        Returns:
            float: Sampled success probability
        """
        import numpy as np
        return np.random.beta(self.bandit_alpha, self.bandit_beta)

    def apply_decay(self, decay_rate: float = 0.99) -> None:
        """
        Apply time-based decay to reduce influence of old data.

        Args:
            decay_rate: Multiplier for decay (0.99 = 1% decay)
        """
        self.bandit_alpha = max(1.0, self.bandit_alpha * decay_rate)
        self.bandit_beta = max(1.0, self.bandit_beta * decay_rate)
        self.decay_factor *= decay_rate
        self.last_decay_at = datetime.utcnow()
