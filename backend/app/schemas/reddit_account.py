"""
Pydantic schemas for Reddit Account endpoints.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RedditAccountBase(BaseModel):
    """Base schema for RedditAccount."""
    username: str = Field(..., min_length=1, max_length=100)


class RedditAccountCreate(RedditAccountBase):
    """Schema for creating a RedditAccount (via OAuth callback)."""
    project_id: Optional[int] = None
    access_token_encrypted: str
    refresh_token_encrypted: str
    token_expires_at: Optional[datetime] = None
    oauth_scopes: Optional[List[str]] = None
    client_id: Optional[str] = None
    client_secret_encrypted: Optional[str] = None
    user_agent: Optional[str] = None


class RedditAccountUpdate(BaseModel):
    """Schema for updating a RedditAccount."""
    project_id: Optional[int] = None
    status: Optional[str] = None
    user_agent: Optional[str] = None


class RedditAccountResponse(RedditAccountBase):
    """Schema for RedditAccount response (public, no tokens)."""
    id: int
    project_id: Optional[int] = None
    display_name: Optional[str] = None

    # Metrics
    karma_total: int
    karma_comment: int
    karma_post: int
    account_age_days: Optional[int] = None

    # Rate limiting
    daily_actions_count: int
    last_action_at: Optional[datetime] = None

    # Health
    status: str
    health_score: float
    last_health_check_at: Optional[datetime] = None

    # Performance
    total_posts_made: int
    total_posts_removed: int
    removal_rate: float

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RedditAccountDetailResponse(RedditAccountResponse):
    """Detailed RedditAccount response."""
    oauth_scopes: Optional[List[str]] = None
    token_expires_at: Optional[datetime] = None
    subreddit_activity: Dict[str, Any] = Field(default_factory=dict)
    can_post: bool = False
    selection_score: float = 0.0


class RedditAccountListResponse(BaseModel):
    """Schema for paginated account list."""
    items: List[RedditAccountResponse]
    total: int


class AccountHealthCheck(BaseModel):
    """Schema for health check result."""
    account_id: int
    username: str
    status: str
    health_score: float
    karma_total: int
    can_post: bool
    issues: List[str] = Field(default_factory=list)


# OAuth schemas
class OAuthInitResponse(BaseModel):
    """Schema for OAuth initialization response."""
    auth_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    """Schema for OAuth callback (query params)."""
    code: str
    state: str


class OAuthCallbackResponse(BaseModel):
    """Schema for OAuth callback response."""
    success: bool
    account_id: Optional[int] = None
    username: Optional[str] = None
    error: Optional[str] = None
