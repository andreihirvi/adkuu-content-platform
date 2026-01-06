"""
Tests for quality gates service.
"""
import pytest
from unittest.mock import MagicMock

from app.services.quality_gates import QualityGates, QualityResult
from app.models import GeneratedContent, Opportunity


class TestQualityGates:
    """Tests for QualityGates service."""

    @pytest.fixture
    def quality_gates(self):
        """Create a QualityGates instance."""
        return QualityGates()

    @pytest.fixture
    def good_content(self):
        """Create content that should pass quality gates."""
        content = MagicMock(spec=GeneratedContent)
        content.content_text = """
        Great question! I'd recommend starting with Python's official tutorial,
        which covers the fundamentals really well. Then you could move on to
        building small projects to practice what you've learned.

        Some resources that helped me:
        - The official Python docs
        - Real Python website
        - Practice problems on LeetCode

        Feel free to ask if you have more questions!
        """
        content.style = "helpful_expert"
        return content

    @pytest.fixture
    def spammy_content(self):
        """Create content that should fail spam check."""
        content = MagicMock(spec=GeneratedContent)
        content.content_text = """
        CHECK OUT THIS AMAZING DEAL!!! 🔥🔥🔥
        Limited time offer! Click here >>> bit.ly/spam123
        You won't believe what happens next!!!
        FREE FREE FREE!!!
        """
        content.style = "casual"
        return content

    @pytest.fixture
    def promotional_content(self):
        """Create content that should fail promotional check."""
        content = MagicMock(spec=GeneratedContent)
        content.content_text = """
        Our product is the best solution for this problem.
        Buy now and get 50% off! Use coupon code SAVE50.
        Visit our website to learn more about our amazing features.
        Sign up for our newsletter to get exclusive deals!
        """
        content.style = "helpful_expert"
        return content

    @pytest.fixture
    def short_content(self):
        """Create content that's too short."""
        content = MagicMock(spec=GeneratedContent)
        content.content_text = "Yes."
        content.style = "casual"
        return content

    @pytest.fixture
    def sample_opportunity(self):
        """Create a mock opportunity."""
        opportunity = MagicMock(spec=Opportunity)
        opportunity.subreddit = "python"
        opportunity.post_title = "How to learn Python?"
        opportunity.post_content = "I want to learn Python programming..."
        return opportunity

    def test_good_content_passes(self, quality_gates, good_content, sample_opportunity):
        """Test that good content passes all quality gates."""
        result = quality_gates.run_all_checks(good_content, sample_opportunity)

        assert result.passed is True
        assert result.overall_score >= 0.7
        assert len(result.failures) == 0

    def test_spammy_content_fails(self, quality_gates, spammy_content, sample_opportunity):
        """Test that spammy content fails quality gates."""
        result = quality_gates.run_all_checks(spammy_content, sample_opportunity)

        assert result.passed is False
        assert "spam" in str(result.failures).lower() or result.overall_score < 0.7

    def test_promotional_content_fails(self, quality_gates, promotional_content, sample_opportunity):
        """Test that promotional content fails quality gates."""
        result = quality_gates.run_all_checks(promotional_content, sample_opportunity)

        assert result.passed is False

    def test_short_content_fails_length_check(self, quality_gates, short_content, sample_opportunity):
        """Test that very short content fails length check."""
        result = quality_gates.run_all_checks(short_content, sample_opportunity)

        assert result.passed is False

    def test_spam_check_detects_excessive_caps(self, quality_gates):
        """Test spam detection for excessive capitalization."""
        content = MagicMock(spec=GeneratedContent)
        content.content_text = "THIS IS ALL CAPS AND VERY SPAMMY LOOKING TEXT!!!"
        content.style = "casual"

        result = quality_gates._check_spam(content)
        assert result["score"] > 0.2  # Should flag as potentially spammy

    def test_promotional_check_detects_cta(self, quality_gates):
        """Test promotional detection for call-to-action phrases."""
        content = MagicMock(spec=GeneratedContent)
        content.content_text = "Buy now! Sign up today! Limited time offer! Visit our website!"
        content.style = "helpful_expert"

        result = quality_gates._check_promotional(content)
        assert result["score"] > 0.3  # Should flag as promotional

    def test_authenticity_check_for_natural_text(self, quality_gates, good_content):
        """Test that natural-sounding text has high authenticity score."""
        result = quality_gates._check_authenticity(good_content)
        assert result["score"] >= 0.6

    def test_quality_result_to_dict(self, quality_gates, good_content, sample_opportunity):
        """Test that quality result can be serialized to dict."""
        result = quality_gates.run_all_checks(good_content, sample_opportunity)
        result_dict = result.to_dict()

        assert "passed" in result_dict
        assert "overall_score" in result_dict
        assert "checks" in result_dict
        assert isinstance(result_dict["checks"], dict)

    def test_subreddit_compliance_check(self, quality_gates, good_content, sample_opportunity):
        """Test subreddit compliance checking."""
        result = quality_gates._check_subreddit_compliance(good_content, sample_opportunity)
        assert "passed" in result
        assert "issues" in result

    def test_run_all_checks_without_opportunity(self, quality_gates, good_content):
        """Test running quality checks without an opportunity."""
        result = quality_gates.run_all_checks(good_content, None)
        # Should still work, just skip subreddit-specific checks
        assert isinstance(result, QualityResult)
