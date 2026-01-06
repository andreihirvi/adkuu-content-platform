"""
Tests for opportunity miner service.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.services.opportunity_miner import OpportunityMiner
from app.utils.reddit_helpers import calculate_post_velocity, classify_urgency


class TestOpportunityMiner:
    """Tests for OpportunityMiner service."""

    @pytest.fixture
    def miner(self):
        """Create an OpportunityMiner instance."""
        return OpportunityMiner()

    @pytest.fixture
    def mock_submission(self):
        """Create a mock Reddit submission."""
        submission = MagicMock()
        submission.id = "test123"
        submission.title = "How to learn Python effectively?"
        submission.selftext = "I'm new to programming and want to learn Python..."
        submission.score = 50
        submission.num_comments = 15
        submission.upvote_ratio = 0.95
        submission.created_utc = (datetime.utcnow() - timedelta(hours=1)).timestamp()
        submission.author = MagicMock()
        submission.author.name = "test_user"
        submission.permalink = "/r/python/comments/test123"
        submission.url = "https://reddit.com/r/python/comments/test123"
        submission.subreddit = MagicMock()
        submission.subreddit.display_name = "python"
        return submission

    def test_velocity_calculation_new_post(self, mock_submission):
        """Test velocity calculation for a new post."""
        velocity = calculate_post_velocity(mock_submission)
        # With score=50 and age=1 hour, velocity should be significant
        assert velocity > 0
        assert isinstance(velocity, float)

    def test_velocity_calculation_old_post(self, mock_submission):
        """Test velocity calculation for an older post."""
        mock_submission.created_utc = (datetime.utcnow() - timedelta(hours=24)).timestamp()
        velocity = calculate_post_velocity(mock_submission)
        # Older posts should have lower velocity
        assert velocity > 0

    def test_urgency_classification_urgent(self):
        """Test urgency classification for urgent posts."""
        urgency = classify_urgency(velocity=100, age_hours=0.5, threshold=15)
        assert urgency == "urgent"

    def test_urgency_classification_high(self):
        """Test urgency classification for high priority posts."""
        urgency = classify_urgency(velocity=20, age_hours=1.5, threshold=15)
        assert urgency == "high"

    def test_urgency_classification_medium(self):
        """Test urgency classification for medium priority posts."""
        urgency = classify_urgency(velocity=10, age_hours=3, threshold=15)
        assert urgency == "medium"

    def test_urgency_classification_low(self):
        """Test urgency classification for low priority posts."""
        urgency = classify_urgency(velocity=5, age_hours=6, threshold=15)
        assert urgency == "low"

    def test_relevance_scoring(self, miner, mock_submission, sample_project):
        """Test relevance score calculation."""
        score = miner._calculate_relevance_score(mock_submission, sample_project)
        assert 0 <= score <= 1
        assert isinstance(score, float)

    def test_relevance_scoring_with_keywords(self, miner, mock_submission, sample_project):
        """Test that keyword matches increase relevance score."""
        # Ensure keywords match the submission title
        sample_project.keywords = ["python", "learn"]
        score = miner._calculate_relevance_score(mock_submission, sample_project)
        # Should have higher relevance due to keyword match
        assert score > 0.5

    def test_composite_score_calculation(self, miner):
        """Test composite score calculation from individual scores."""
        composite = miner._calculate_composite_score(
            relevance=0.8,
            virality=0.7,
            timing=0.9,
        )
        assert 0 <= composite <= 1
        # Verify weighting
        expected = 0.8 * 0.30 + 0.7 * 0.25 + 0.9 * 0.40 + 0.5 * 0.05
        assert abs(composite - expected) < 0.01

    def test_expiration_time_calculation(self, miner):
        """Test expiration time based on urgency."""
        now = datetime.utcnow()

        urgent_expires = miner._calculate_expiration("urgent", now)
        assert urgent_expires <= now + timedelta(minutes=30)

        high_expires = miner._calculate_expiration("high", now)
        assert high_expires <= now + timedelta(hours=2)

        medium_expires = miner._calculate_expiration("medium", now)
        assert medium_expires <= now + timedelta(hours=4)

        low_expires = miner._calculate_expiration("low", now)
        assert low_expires <= now + timedelta(hours=24)

    @patch('app.services.opportunity_miner.praw.Reddit')
    def test_mine_subreddit(self, mock_reddit_class, miner, sample_project, db, mock_submission):
        """Test mining a single subreddit."""
        mock_reddit = MagicMock()
        mock_subreddit = MagicMock()
        mock_subreddit.rising.return_value = [mock_submission]
        mock_subreddit.new.return_value = []
        mock_reddit.subreddit.return_value = mock_subreddit
        mock_reddit_class.return_value = mock_reddit

        miner._reddit_client = mock_reddit

        opportunities = miner._mine_subreddit(
            db=db,
            project=sample_project,
            subreddit_name="python",
            limit=10
        )

        assert isinstance(opportunities, list)

    def test_is_duplicate_check(self, miner, db, sample_opportunity):
        """Test duplicate detection."""
        # Should detect existing opportunity
        is_dup = miner._is_duplicate(db, sample_opportunity.reddit_post_id)
        assert is_dup is True

        # Should not detect non-existent
        is_dup = miner._is_duplicate(db, "nonexistent123")
        assert is_dup is False

    def test_velocity_threshold_by_subreddit_size(self, miner):
        """Test velocity thresholds based on subreddit size."""
        # Small subreddit
        threshold = miner._get_velocity_threshold(10000)
        assert threshold == 5

        # Medium subreddit
        threshold = miner._get_velocity_threshold(200000)
        assert threshold == 15

        # Large subreddit
        threshold = miner._get_velocity_threshold(1000000)
        assert threshold == 50

        # Very large subreddit
        threshold = miner._get_velocity_threshold(5000000)
        assert threshold == 200
