"""
Project model - represents a product/service to advertise.
"""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship, Mapped
import enum

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.reddit_account import RedditAccount
    from app.models.subreddit_config import SubredditConfig
    from app.models.generated_content import GeneratedContent


class ProjectStatus(str, enum.Enum):
    """Project status enum."""
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class AutomationLevel(int, enum.Enum):
    """Automation level for content publishing."""
    MANUAL = 1         # All content requires human review
    ASSISTED = 2       # High-confidence content queued, approval required
    SEMI_AUTO = 3      # Safe content auto-approved, risky needs review
    FULL_AUTO = 4      # ML-driven selection and publishing


class Project(Base):
    """
    Project model representing a product/service to advertise on Reddit.

    A project defines:
    - Target subreddits to monitor
    - Keywords to match opportunities
    - Brand voice for content generation
    - Automation settings
    """

    __tablename__ = "projects"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = Column(Text, nullable=True)

    # Brand voice and product context for content generation
    brand_voice: Mapped[Optional[str]] = Column(Text, nullable=True)
    product_context: Mapped[Optional[str]] = Column(Text, nullable=True)
    website_url: Mapped[Optional[str]] = Column(String(500), nullable=True)

    # Target configuration (stored as JSON arrays)
    target_subreddits: Mapped[List] = Column(JSON, default=list, nullable=False)
    keywords: Mapped[List] = Column(JSON, default=list, nullable=False)
    negative_keywords: Mapped[List] = Column(JSON, default=list, nullable=False)

    # Automation settings
    automation_level: Mapped[int] = Column(
        Integer,
        default=AutomationLevel.MANUAL.value,
        nullable=False
    )

    # Project status
    status: Mapped[str] = Column(
        String(50),
        default=ProjectStatus.ACTIVE.value,
        nullable=False,
        index=True
    )

    # Additional settings (flexible JSON storage)
    settings: Mapped[dict] = Column(JSON, default=dict, nullable=False)

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
    opportunities: Mapped[List["Opportunity"]] = relationship(
        "Opportunity",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    reddit_accounts: Mapped[List["RedditAccount"]] = relationship(
        "RedditAccount",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    subreddit_configs: Mapped[List["SubredditConfig"]] = relationship(
        "SubredditConfig",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    generated_contents: Mapped[List["GeneratedContent"]] = relationship(
        "GeneratedContent",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"
