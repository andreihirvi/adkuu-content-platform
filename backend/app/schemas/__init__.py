"""
Pydantic schemas for Adkuu Content Platform API.
"""
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    SubredditConfigCreate,
    SubredditConfigUpdate,
    SubredditConfigResponse,
)
from app.schemas.opportunity import (
    OpportunityCreate,
    OpportunityResponse,
    OpportunityDetailResponse,
    OpportunityListResponse,
    OpportunityFilter,
    MiningRequest,
    MiningResult,
    ApproveRejectRequest,
)
from app.schemas.content import (
    ContentCreate,
    ContentUpdate,
    ContentResponse,
    ContentDetailResponse,
    ContentListResponse,
    ContentFilter,
    GenerateContentRequest,
    PublishContentRequest,
    PublishResult,
    RegenerateRequest,
    PerformanceSnapshot,
    ContentPerformanceResponse,
)
from app.schemas.reddit_account import (
    RedditAccountCreate,
    RedditAccountUpdate,
    RedditAccountResponse,
    RedditAccountDetailResponse,
    RedditAccountListResponse,
    AccountHealthCheck,
    OAuthInitResponse,
    OAuthCallbackRequest,
    OAuthCallbackResponse,
)
from app.schemas.analytics import (
    ProjectAnalytics,
    TimeSeriesDataPoint,
    PerformanceTimeSeries,
    SubredditInsights,
    LearningFeatureResponse,
    LearningInsights,
    DashboardSummary,
)

__all__ = [
    # Project
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectDetailResponse",
    "ProjectListResponse",
    "SubredditConfigCreate",
    "SubredditConfigUpdate",
    "SubredditConfigResponse",
    # Opportunity
    "OpportunityCreate",
    "OpportunityResponse",
    "OpportunityDetailResponse",
    "OpportunityListResponse",
    "OpportunityFilter",
    "MiningRequest",
    "MiningResult",
    "ApproveRejectRequest",
    # Content
    "ContentCreate",
    "ContentUpdate",
    "ContentResponse",
    "ContentDetailResponse",
    "ContentListResponse",
    "ContentFilter",
    "GenerateContentRequest",
    "PublishContentRequest",
    "PublishResult",
    "RegenerateRequest",
    "PerformanceSnapshot",
    "ContentPerformanceResponse",
    # Reddit Account
    "RedditAccountCreate",
    "RedditAccountUpdate",
    "RedditAccountResponse",
    "RedditAccountDetailResponse",
    "RedditAccountListResponse",
    "AccountHealthCheck",
    "OAuthInitResponse",
    "OAuthCallbackRequest",
    "OAuthCallbackResponse",
    # Analytics
    "ProjectAnalytics",
    "TimeSeriesDataPoint",
    "PerformanceTimeSeries",
    "SubredditInsights",
    "LearningFeatureResponse",
    "LearningInsights",
    "DashboardSummary",
]
