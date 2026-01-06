"""
Test configuration and fixtures.
"""
import pytest
from typing import Generator
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api.deps import get_db
from app.db.base_class import Base
from app.models import (
    Project, Opportunity, GeneratedContent, RedditAccount,
    SubredditConfig, ContentPerformance, LearningFeature,
    ProjectStatus, OpportunityStatus, ContentStatus, AccountStatus
)

# Test database URL (in-memory SQLite for testing)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator:
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db) -> Generator:
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_project(db) -> Project:
    """Create a sample project."""
    project = Project(
        name="Test Project",
        description="A test project for unit tests",
        brand_voice="Helpful and professional",
        target_subreddits=["python", "programming", "learnpython"],
        keywords=["python", "programming", "coding"],
        product_context="A developer tools company",
        website_url="https://example.com",
        automation_level=2,
        status=ProjectStatus.ACTIVE.value,
        settings={},
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@pytest.fixture
def sample_opportunity(db, sample_project) -> Opportunity:
    """Create a sample opportunity."""
    opportunity = Opportunity(
        project_id=sample_project.id,
        reddit_post_id="abc123",
        subreddit="python",
        post_title="How to learn Python effectively?",
        post_content="I'm new to programming and want to learn Python...",
        post_url="https://reddit.com/r/python/comments/abc123",
        post_author="test_user",
        post_created_at=datetime.utcnow() - timedelta(hours=1),
        post_score=50,
        post_num_comments=10,
        post_upvote_ratio=0.95,
        relevance_score=0.85,
        virality_score=0.70,
        timing_score=0.90,
        composite_score=0.82,
        urgency="high",
        status=OpportunityStatus.PENDING.value,
        expires_at=datetime.utcnow() + timedelta(hours=2),
        discovered_at=datetime.utcnow(),
    )
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@pytest.fixture
def sample_content(db, sample_project, sample_opportunity) -> GeneratedContent:
    """Create sample generated content."""
    content = GeneratedContent(
        opportunity_id=sample_opportunity.id,
        project_id=sample_project.id,
        content_text="Great question! I'd recommend starting with...",
        content_type="comment",
        style="helpful_expert",
        quality_score=0.85,
        quality_checks={
            "spam_check": {"passed": True, "score": 0.05},
            "promotional_check": {"passed": True, "score": 0.1},
            "authenticity_check": {"passed": True, "score": 0.9},
        },
        passed_quality_gates=True,
        status=ContentStatus.PENDING.value,
        version=1,
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return content


@pytest.fixture
def sample_account(db, sample_project) -> RedditAccount:
    """Create a sample Reddit account."""
    account = RedditAccount(
        project_id=sample_project.id,
        username="test_account",
        display_name="Test Account",
        refresh_token_encrypted="encrypted_token_here",
        client_id="test_client_id",
        user_agent="test_user_agent",
        karma_total=5000,
        karma_comment=3000,
        karma_post=2000,
        account_age_days=365,
        status=AccountStatus.ACTIVE.value,
        health_score=1.0,
        daily_actions_count=0,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def sample_subreddit_config(db, sample_project) -> SubredditConfig:
    """Create a sample subreddit configuration."""
    config = SubredditConfig(
        project_id=sample_project.id,
        subreddit_name="python",
        subscribers=1000000,
        active_users=5000,
        min_account_age_days=30,
        min_karma=100,
        posting_rules="Be helpful. No spam.",
        best_posting_hours=[9, 10, 11, 14, 15, 16],
        best_posting_days=[1, 2, 3, 4, 5],  # Mon-Fri
        avg_post_score=50.0,
        velocity_threshold=15.0,
        is_enabled=True,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@pytest.fixture
def mock_reddit_client():
    """Create a mock PRAW Reddit client."""
    mock_client = MagicMock()

    # Mock submission
    mock_submission = MagicMock()
    mock_submission.id = "test123"
    mock_submission.title = "Test Post"
    mock_submission.selftext = "Test content"
    mock_submission.score = 100
    mock_submission.num_comments = 20
    mock_submission.upvote_ratio = 0.95
    mock_submission.created_utc = datetime.utcnow().timestamp() - 3600
    mock_submission.author.name = "test_author"
    mock_submission.permalink = "/r/test/comments/test123"
    mock_submission.url = "https://reddit.com/r/test/comments/test123"

    # Mock subreddit
    mock_subreddit = MagicMock()
    mock_subreddit.display_name = "python"
    mock_subreddit.subscribers = 1000000
    mock_subreddit.rising.return_value = [mock_submission]
    mock_subreddit.new.return_value = [mock_submission]

    mock_client.subreddit.return_value = mock_subreddit

    # Mock comment reply
    mock_comment = MagicMock()
    mock_comment.id = "comment123"
    mock_comment.permalink = "/r/test/comments/test123/comment123"
    mock_submission.reply.return_value = mock_comment

    return mock_client


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock_client = MagicMock()

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="This is a generated response that provides helpful information."
            )
        )
    ]

    mock_client.chat.completions.create.return_value = mock_response

    return mock_client
