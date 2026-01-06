"""
Pydantic schemas for Opportunity endpoints.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class OpportunityBase(BaseModel):
    """Base schema for Opportunity."""
    reddit_post_id: str
    subreddit: str
    post_title: str
    post_content: Optional[str] = None
    post_url: str
    post_author: Optional[str] = None


class OpportunityCreate(OpportunityBase):
    """Schema for creating an Opportunity (internal use)."""
    project_id: int
    post_created_at: Optional[datetime] = None
    post_score: int = 0
    post_num_comments: int = 0
    post_upvote_ratio: Optional[float] = None
    relevance_score: Optional[float] = None
    virality_score: Optional[float] = None
    timing_score: Optional[float] = None
    composite_score: Optional[float] = None
    urgency: Optional[str] = None
    velocity: Optional[float] = None
    opportunity_metadata: Dict[str, Any] = Field(default_factory=dict)


class OpportunityResponse(OpportunityBase):
    """Schema for Opportunity response."""
    id: int
    project_id: int
    post_created_at: Optional[datetime] = None
    post_score: int
    post_num_comments: int
    post_upvote_ratio: Optional[float] = None

    # Scoring
    relevance_score: Optional[float] = None
    virality_score: Optional[float] = None
    timing_score: Optional[float] = None
    composite_score: Optional[float] = None
    urgency: Optional[str] = None
    velocity: Optional[float] = None

    # Status
    status: str
    expires_at: Optional[datetime] = None
    discovered_at: datetime
    processed_at: Optional[datetime] = None

    # Metadata
    opportunity_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class OpportunityDetailResponse(OpportunityResponse):
    """Detailed Opportunity response with content."""
    generated_content_count: int = 0
    latest_content_id: Optional[int] = None
    latest_content_status: Optional[str] = None


class OpportunityListResponse(BaseModel):
    """Schema for paginated opportunity list."""
    items: List[OpportunityResponse]
    total: int
    skip: int
    limit: int


class OpportunityFilter(BaseModel):
    """Schema for filtering opportunities."""
    project_id: Optional[int] = None
    status: Optional[str] = None
    subreddit: Optional[str] = None
    min_score: Optional[float] = None
    urgency: Optional[str] = None
    include_expired: bool = False


class MiningRequest(BaseModel):
    """Schema for manual mining request."""
    project_id: int
    subreddits: Optional[List[str]] = None
    limit: int = Field(default=100, le=500)


class MiningResult(BaseModel):
    """Schema for mining result."""
    task_id: Optional[str] = None
    opportunities_found: int
    opportunities_new: int
    status: str
    message: Optional[str] = None


class ApproveRejectRequest(BaseModel):
    """Schema for approve/reject requests."""
    reason: Optional[str] = None
