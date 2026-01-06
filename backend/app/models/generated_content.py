"""
GeneratedContent model - represents LLM-generated content for opportunities.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship, Mapped
import enum

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.opportunity import Opportunity
    from app.models.reddit_account import RedditAccount
    from app.models.content_performance import ContentPerformance


class ContentStatus(str, enum.Enum):
    """Status of generated content in the pipeline."""
    DRAFT = "draft"           # Just generated, awaiting quality check
    PENDING = "pending"       # Passed quality gates, awaiting review
    APPROVED = "approved"     # Approved for publishing
    REJECTED = "rejected"     # Rejected by user or quality gates
    PUBLISHING = "publishing" # Currently being published
    PUBLISHED = "published"   # Successfully published
    FAILED = "failed"         # Failed to publish
    DELETED = "deleted"       # Removed from Reddit


class ContentType(str, enum.Enum):
    """Type of content generated."""
    COMMENT = "comment"       # Reply to a post
    POST = "post"            # New post
    REPLY = "reply"          # Reply to a comment


class ContentStyle(str, enum.Enum):
    """Style/tone of the generated content."""
    HELPFUL_EXPERT = "helpful_expert"   # Professional, knowledgeable
    CASUAL = "casual"                   # Friendly, conversational
    TECHNICAL = "technical"             # Detailed, technical
    STORYTELLING = "storytelling"       # Personal narrative


class GeneratedContent(Base):
    """
    GeneratedContent model for LLM-generated Reddit content.

    Contains:
    - The generated text content
    - Quality scores and checks
    - Publishing status and metadata
    - Version tracking for regenerations
    """

    __tablename__ = "generated_contents"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    opportunity_id: Mapped[Optional[int]] = Column(
        Integer,
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    project_id: Mapped[int] = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Content
    content_text: Mapped[str] = Column(Text, nullable=False)
    content_type: Mapped[str] = Column(
        String(50),
        default=ContentType.COMMENT.value,
        nullable=False
    )
    style: Mapped[Optional[str]] = Column(String(50), nullable=True)

    # Quality assessment
    quality_score: Mapped[Optional[float]] = Column(Float, nullable=True)  # 0-1
    quality_checks: Mapped[dict] = Column(JSON, default=dict, nullable=False)
    passed_quality_gates: Mapped[bool] = Column(Boolean, default=False, nullable=False)

    # Status tracking
    status: Mapped[str] = Column(
        String(50),
        default=ContentStatus.DRAFT.value,
        nullable=False,
        index=True
    )
    rejection_reason: Mapped[Optional[str]] = Column(Text, nullable=True)

    # Publishing information
    reddit_account_id: Mapped[Optional[int]] = Column(
        Integer,
        ForeignKey("reddit_accounts.id", ondelete="SET NULL"),
        nullable=True
    )
    published_reddit_id: Mapped[Optional[str]] = Column(String(50), nullable=True)
    published_url: Mapped[Optional[str]] = Column(String(500), nullable=True)
    published_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    # Versioning (for regenerations)
    version: Mapped[int] = Column(Integer, default=1, nullable=False)
    parent_content_id: Mapped[Optional[int]] = Column(Integer, nullable=True)

    # LLM metadata
    content_metadata: Mapped[dict] = Column(JSON, default=dict, nullable=False)
    # Stores: model_used, temperature, prompt_tokens, completion_tokens, etc.

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
    project: Mapped["Project"] = relationship("Project", back_populates="generated_contents")
    opportunity: Mapped[Optional["Opportunity"]] = relationship(
        "Opportunity",
        back_populates="generated_contents"
    )
    reddit_account: Mapped[Optional["RedditAccount"]] = relationship(
        "RedditAccount",
        back_populates="generated_contents"
    )
    performance_snapshots: Mapped[List["ContentPerformance"]] = relationship(
        "ContentPerformance",
        back_populates="content",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<GeneratedContent(id={self.id}, status='{self.status}', version={self.version})>"

    @property
    def is_published(self) -> bool:
        """Check if content has been published."""
        return self.status == ContentStatus.PUBLISHED.value and self.published_reddit_id is not None

    @property
    def word_count(self) -> int:
        """Get word count of content."""
        return len(self.content_text.split())
