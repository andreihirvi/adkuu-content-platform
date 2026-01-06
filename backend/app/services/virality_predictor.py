"""
Virality Prediction Service - predicts engagement potential of posts.
"""
import logging
from typing import Dict, Any, Optional
import praw
from datetime import datetime

from app.utils.reddit_helpers import get_post_age_hours

logger = logging.getLogger(__name__)


class ViralityPredictor:
    """
    Service for predicting virality/engagement potential of Reddit posts.

    Phase 0: Uses heuristic-based scoring
    Phase 1+: Will use ML model (XGBoost/LightGBM) trained on Reddit data
    """

    def __init__(self):
        self.model = None  # Placeholder for ML model
        self._load_model()

    def _load_model(self):
        """Load ML model if available."""
        # TODO: Load trained model from file/database
        # For now, using heuristic approach
        pass

    def predict(
        self,
        submission: praw.models.Submission,
        velocity_threshold: float
    ) -> float:
        """
        Predict virality score for a submission.

        Args:
            submission: Reddit submission
            velocity_threshold: Subreddit's velocity threshold

        Returns:
            float: Virality score (0-1)
        """
        if self.model:
            return self._predict_ml(submission, velocity_threshold)
        else:
            return self._predict_heuristic(submission, velocity_threshold)

    def _predict_heuristic(
        self,
        submission: praw.models.Submission,
        velocity_threshold: float
    ) -> float:
        """
        Heuristic-based virality prediction.

        Uses multiple signals to estimate engagement potential.
        """
        score = 0.5  # Base score

        # Extract features
        features = self._extract_features(submission)

        # 1. Velocity signal (most important)
        velocity = features["velocity"]
        if velocity > velocity_threshold * 2:
            score += 0.25
        elif velocity > velocity_threshold:
            score += 0.15
        elif velocity > velocity_threshold * 0.5:
            score += 0.05

        # 2. Early engagement signal
        age_hours = features["age_hours"]
        if age_hours < 1:
            # Very new post with good engagement
            if submission.score > 10:
                score += 0.1
            if submission.num_comments > 5:
                score += 0.1
        elif age_hours < 2:
            if submission.score > 50:
                score += 0.1

        # 3. Upvote ratio signal
        upvote_ratio = features["upvote_ratio"]
        if upvote_ratio > 0.9:
            score += 0.1
        elif upvote_ratio > 0.8:
            score += 0.05
        elif upvote_ratio < 0.6:
            score -= 0.1

        # 4. Title quality signals
        title_length = features["title_length"]
        if 40 <= title_length <= 120:
            score += 0.05

        has_question = features["has_question"]
        if has_question:
            score += 0.05

        # 5. Content type signals
        is_self = features["is_self"]
        if is_self and features["body_length"] > 100:
            score += 0.05

        # 6. Subreddit engagement signals
        subreddit_size = features["subreddit_subscribers"]
        comments_per_subscriber = submission.num_comments / max(subreddit_size, 1)
        if comments_per_subscriber > 0.0001:  # High engagement relative to size
            score += 0.1

        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))

    def _predict_ml(
        self,
        submission: praw.models.Submission,
        velocity_threshold: float
    ) -> float:
        """
        ML-based virality prediction.

        Uses trained XGBoost/LightGBM model.
        """
        features = self._extract_features(submission)
        feature_vector = self._features_to_vector(features, velocity_threshold)

        try:
            # Predict probability
            proba = self.model.predict_proba([feature_vector])[0][1]
            return float(proba)
        except Exception as e:
            logger.error(f"ML prediction failed, falling back to heuristic: {e}")
            return self._predict_heuristic(submission, velocity_threshold)

    def _extract_features(self, submission: praw.models.Submission) -> Dict[str, Any]:
        """
        Extract features from a submission for prediction.

        Returns features that are available at time of discovery
        (not outcomes like final score).
        """
        age_hours = get_post_age_hours(submission)
        age_hours = max(0.1, age_hours)  # Avoid division by zero

        # Calculate velocity
        score_velocity = submission.score / age_hours
        comment_velocity = submission.num_comments / age_hours
        velocity = (score_velocity * 0.7) + (comment_velocity * 0.3 * 10)

        return {
            # Temporal features
            "age_hours": age_hours,
            "hour_of_day": datetime.utcfromtimestamp(submission.created_utc).hour,
            "day_of_week": datetime.utcfromtimestamp(submission.created_utc).weekday(),
            "is_weekend": datetime.utcfromtimestamp(submission.created_utc).weekday() >= 5,

            # Engagement features (at discovery time)
            "score": submission.score,
            "num_comments": submission.num_comments,
            "upvote_ratio": submission.upvote_ratio,
            "velocity": velocity,
            "score_velocity": score_velocity,
            "comment_velocity": comment_velocity,

            # Title features
            "title_length": len(submission.title),
            "title_word_count": len(submission.title.split()),
            "has_question": "?" in submission.title,
            "has_number": any(c.isdigit() for c in submission.title),
            "is_all_caps": submission.title.isupper(),

            # Content features
            "is_self": submission.is_self,
            "body_length": len(submission.selftext) if submission.is_self else 0,
            "has_link": not submission.is_self,
            "is_video": hasattr(submission, 'is_video') and submission.is_video,
            "is_image": self._is_image_post(submission),

            # Subreddit features
            "subreddit": submission.subreddit.display_name,
            "subreddit_subscribers": submission.subreddit.subscribers,

            # Author features (if available)
            "author_karma": self._get_author_karma(submission),
            "author_account_age_days": self._get_author_age(submission),
        }

    def _features_to_vector(
        self,
        features: Dict[str, Any],
        velocity_threshold: float
    ) -> list:
        """Convert features dict to numeric vector for ML model."""
        return [
            features["age_hours"],
            features["hour_of_day"],
            features["day_of_week"],
            1 if features["is_weekend"] else 0,
            features["score"],
            features["num_comments"],
            features["upvote_ratio"],
            features["velocity"],
            features["velocity"] / max(velocity_threshold, 1),  # Normalized velocity
            features["title_length"],
            features["title_word_count"],
            1 if features["has_question"] else 0,
            1 if features["has_number"] else 0,
            1 if features["is_self"] else 0,
            features["body_length"],
            features["subreddit_subscribers"],
            features["author_karma"] or 0,
            features["author_account_age_days"] or 0,
        ]

    def _is_image_post(self, submission: praw.models.Submission) -> bool:
        """Check if submission is an image post."""
        if submission.is_self:
            return False

        image_domains = ['i.redd.it', 'imgur.com', 'i.imgur.com']
        return any(domain in submission.url for domain in image_domains)

    def _get_author_karma(self, submission: praw.models.Submission) -> Optional[int]:
        """Get author's total karma if available."""
        try:
            if submission.author:
                return submission.author.total_karma
        except Exception:
            pass
        return None

    def _get_author_age(self, submission: praw.models.Submission) -> Optional[int]:
        """Get author's account age in days if available."""
        try:
            if submission.author:
                created = datetime.utcfromtimestamp(submission.author.created_utc)
                return (datetime.utcnow() - created).days
        except Exception:
            pass
        return None

    def retrain(self, training_data: list) -> bool:
        """
        Retrain the ML model with new data.

        Args:
            training_data: List of (features, label) tuples

        Returns:
            bool: Success status
        """
        # TODO: Implement model retraining
        # - Load existing model
        # - Add new training examples
        # - Retrain with updated data
        # - Validate performance
        # - Save if improved
        logger.info("Model retraining not yet implemented")
        return False
