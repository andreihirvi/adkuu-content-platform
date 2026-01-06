"""
Pydantic schemas for Content endpoints.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ContentBase(BaseModel):
    """Base schema for GeneratedContent."""
    content_text: str = Field(..., min_length=1)
    content_type: str = "comment"
    style: Optional[str] = None


class ContentCreate(ContentBase):
    """Schema for creating content (internal use)."""
    opportunity_id: Optional[int] = None
    project_id: int
    quality_score: Optional[float] = None
    quality_checks: Dict[str, Any] = Field(default_factory=dict)
    passed_quality_gates: bool = False
    content_metadata: Dict[str, Any] = Field(default_factory=dict)


class ContentUpdate(BaseModel):
    """Schema for updating content."""
    content_text: Optional[str] = Field(None, min_length=1)
    style: Optional[str] = None


class ContentResponse(ContentBase):
    """Schema for Content response."""
    id: int
    opportunity_id: Optional[int] = None
    project_id: int

    # Quality
    quality_score: Optional[float] = None
    quality_checks: Dict[str, Any] = Field(default_factory=dict)
    passed_quality_gates: bool

    # Status
    status: str
    rejection_reason: Optional[str] = None

    # Publishing
    reddit_account_id: Optional[int] = None
    published_reddit_id: Optional[str] = None
    published_url: Optional[str] = None
    published_at: Optional[datetime] = None

    # Versioning
    version: int
    parent_content_id: Optional[int] = None

    # Metadata
    content_metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContentDetailResponse(ContentResponse):
    """Detailed Content response with opportunity and performance."""
    opportunity_title: Optional[str] = None
    opportunity_subreddit: Optional[str] = None
    latest_score: Optional[int] = None
    latest_num_replies: Optional[int] = None
    is_removed: bool = False


class ContentListResponse(BaseModel):
    """Schema for paginated content list."""
    items: List[ContentResponse]
    total: int
    skip: int
    limit: int


class ContentFilter(BaseModel):
    """Schema for filtering content."""
    project_id: Optional[int] = None
    opportunity_id: Optional[int] = None
    status: Optional[str] = None
    passed_quality: Optional[bool] = None


class GenerateContentRequest(BaseModel):
    """Schema for content generation request."""
    style: str = Field(default="helpful_expert")
    regenerate: bool = False
    feedback: Optional[str] = None


class PublishContentRequest(BaseModel):
    """Schema for publish request."""
    account_id: Optional[int] = None


class PublishResult(BaseModel):
    """Schema for publish result."""
    success: bool
    content_id: int
    published_reddit_id: Optional[str] = None
    published_url: Optional[str] = None
    error: Optional[str] = None


class RegenerateRequest(BaseModel):
    """Schema for regenerate request."""
    feedback: Optional[str] = None
    style: Optional[str] = None


# Performance schemas
class PerformanceSnapshot(BaseModel):
    """Schema for performance snapshot."""
    id: int
    content_id: int
    snapshot_at: datetime
    score: int
    upvotes: int
    downvotes: int
    num_replies: int
    engagement_rate: Optional[float] = None
    velocity: Optional[float] = None
    is_removed: bool
    removal_reason: Optional[str] = None

    class Config:
        from_attributes = True


class ContentPerformanceResponse(BaseModel):
    """Schema for content performance with history."""
    content_id: int
    current_score: int
    current_replies: int
    is_removed: bool
    snapshots: List[PerformanceSnapshot]
    total_snapshots: int
