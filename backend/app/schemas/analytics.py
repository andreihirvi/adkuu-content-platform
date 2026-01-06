"""
Pydantic schemas for Analytics endpoints.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ProjectAnalytics(BaseModel):
    """Schema for project analytics summary."""
    project_id: int
    project_name: str
    period_days: int

    # Opportunity metrics
    total_opportunities: int
    pending_opportunities: int
    approved_opportunities: int
    published_opportunities: int
    expired_opportunities: int

    # Content metrics
    total_content_generated: int
    content_approved: int
    content_published: int
    content_rejected: int

    # Performance metrics
    avg_content_score: Optional[float] = None
    total_engagement: int
    removal_rate: float

    # Timing metrics
    avg_time_to_publish_minutes: Optional[float] = None
    urgent_published_in_time_pct: Optional[float] = None

    # Top performing
    top_subreddits: List[Dict[str, Any]] = Field(default_factory=list)
    best_posting_hours: List[int] = Field(default_factory=list)


class TimeSeriesDataPoint(BaseModel):
    """Schema for a single time series data point."""
    timestamp: datetime
    value: float
    label: Optional[str] = None


class PerformanceTimeSeries(BaseModel):
    """Schema for performance time series data."""
    project_id: int
    metric: str
    granularity: str  # hour, day, week
    data: List[TimeSeriesDataPoint]
    total_points: int


class SubredditInsights(BaseModel):
    """Schema for subreddit insights."""
    subreddit_name: str
    subscribers: Optional[int] = None

    # Our performance
    total_posts: int
    successful_posts: int
    avg_score: Optional[float] = None
    removal_rate: float

    # Timing insights
    best_hours: List[int] = Field(default_factory=list)
    best_days: List[int] = Field(default_factory=list)

    # Velocity info
    velocity_threshold: float
    avg_post_velocity: Optional[float] = None

    # Recommendations
    recommendations: List[str] = Field(default_factory=list)


class LearningFeatureResponse(BaseModel):
    """Schema for learning feature data."""
    id: int
    feature_type: str
    feature_key: str
    project_id: Optional[int] = None

    sample_count: int
    success_rate: Optional[float] = None
    avg_score: Optional[float] = None
    confidence: Optional[float] = None

    feature_data: Dict[str, Any] = Field(default_factory=dict)
    last_updated_at: datetime

    class Config:
        from_attributes = True


class LearningInsights(BaseModel):
    """Schema for learning insights."""
    project_id: int

    # What's working
    top_performing_subreddits: List[Dict[str, Any]] = Field(default_factory=list)
    top_performing_keywords: List[Dict[str, Any]] = Field(default_factory=list)
    best_content_styles: List[Dict[str, Any]] = Field(default_factory=list)

    # What to avoid
    underperforming_subreddits: List[Dict[str, Any]] = Field(default_factory=list)
    high_removal_patterns: List[str] = Field(default_factory=list)

    # Recommendations
    suggested_subreddits: List[str] = Field(default_factory=list)
    suggested_keywords: List[str] = Field(default_factory=list)
    timing_recommendations: Dict[str, Any] = Field(default_factory=dict)


class DashboardSummary(BaseModel):
    """Schema for dashboard summary."""
    # Today's stats
    opportunities_today: int
    content_published_today: int
    engagement_today: int

    # Pending actions
    pending_review: int
    urgent_opportunities: int

    # Health
    active_accounts: int
    accounts_with_issues: int

    # Recent activity
    recent_publications: List[Dict[str, Any]] = Field(default_factory=list)
    recent_high_performers: List[Dict[str, Any]] = Field(default_factory=list)
