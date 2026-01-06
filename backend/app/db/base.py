"""
Import all models here for Alembic and SQLAlchemy discovery.
"""
from app.db.base_class import Base

# Import all models to register them with SQLAlchemy
from app.models.project import Project
from app.models.opportunity import Opportunity
from app.models.generated_content import GeneratedContent
from app.models.content_performance import ContentPerformance
from app.models.reddit_account import RedditAccount
from app.models.subreddit_config import SubredditConfig
from app.models.learning_feature import LearningFeature

# Export Base for Alembic
__all__ = [
    "Base",
    "Project",
    "Opportunity",
    "GeneratedContent",
    "ContentPerformance",
    "RedditAccount",
    "SubredditConfig",
    "LearningFeature",
]
