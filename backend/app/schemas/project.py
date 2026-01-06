"""
Pydantic schemas for Project endpoints.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class ProjectBase(BaseModel):
    """Base schema for Project."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    brand_voice: Optional[str] = None
    product_context: Optional[str] = None
    website_url: Optional[str] = None
    target_subreddits: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    negative_keywords: List[str] = Field(default_factory=list)
    automation_level: int = Field(default=1, ge=1, le=4)


class ProjectCreate(ProjectBase):
    """Schema for creating a Project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a Project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    brand_voice: Optional[str] = None
    product_context: Optional[str] = None
    website_url: Optional[str] = None
    target_subreddits: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    negative_keywords: Optional[List[str]] = None
    automation_level: Optional[int] = Field(None, ge=1, le=4)
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectResponse(ProjectBase):
    """Schema for Project response."""
    id: int
    status: str
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    """Detailed Project response with statistics."""
    total_opportunities: int = 0
    pending_opportunities: int = 0
    published_content: int = 0
    connected_accounts: int = 0


class ProjectListResponse(BaseModel):
    """Schema for paginated project list."""
    items: List[ProjectResponse]
    total: int
    skip: int
    limit: int


# Subreddit config schemas
class SubredditConfigBase(BaseModel):
    """Base schema for SubredditConfig."""
    subreddit_name: str = Field(..., min_length=1, max_length=100)
    min_account_age_days: Optional[int] = None
    min_karma: Optional[int] = None
    posting_rules: Optional[str] = None
    is_enabled: bool = True


class SubredditConfigCreate(SubredditConfigBase):
    """Schema for creating a SubredditConfig."""
    pass


class SubredditConfigUpdate(BaseModel):
    """Schema for updating a SubredditConfig."""
    min_account_age_days: Optional[int] = None
    min_karma: Optional[int] = None
    posting_rules: Optional[str] = None
    best_posting_hours: Optional[List[int]] = None
    best_posting_days: Optional[List[int]] = None
    velocity_threshold: Optional[float] = None
    is_enabled: Optional[bool] = None


class SubredditConfigResponse(SubredditConfigBase):
    """Schema for SubredditConfig response."""
    id: int
    project_id: int
    subscribers: Optional[int] = None
    active_users: Optional[int] = None
    avg_post_score: Optional[float] = None
    our_avg_score: Optional[float] = None
    our_removal_rate: Optional[float] = None
    best_posting_hours: Optional[List[int]] = None
    velocity_threshold: Optional[float] = None
    last_analyzed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
