"""
Database models for Adkuu Content Platform.
"""
from app.models.project import Project, ProjectStatus, AutomationLevel
from app.models.opportunity import Opportunity, OpportunityStatus, OpportunityUrgency
from app.models.generated_content import GeneratedContent, ContentStatus, ContentType, ContentStyle
from app.models.content_performance import ContentPerformance
from app.models.reddit_account import RedditAccount, AccountStatus
from app.models.subreddit_config import SubredditConfig
from app.models.learning_feature import LearningFeature, FeatureType
from app.models.user import User, UserRole

__all__ = [
    # Models
    "Project",
    "Opportunity",
    "GeneratedContent",
    "ContentPerformance",
    "RedditAccount",
    "SubredditConfig",
    "LearningFeature",
    "User",
    # Enums
    "ProjectStatus",
    "AutomationLevel",
    "OpportunityStatus",
    "OpportunityUrgency",
    "ContentStatus",
    "ContentType",
    "ContentStyle",
    "AccountStatus",
    "FeatureType",
    "UserRole",
]
