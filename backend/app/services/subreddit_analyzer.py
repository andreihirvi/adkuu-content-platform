"""
Subreddit Analyzer Service - analyzes subreddits for optimal posting.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import praw
from sqlalchemy.orm import Session

from app.models import SubredditConfig
from app.utils.reddit_helpers import RedditClientFactory, get_velocity_threshold

logger = logging.getLogger(__name__)


class SubredditAnalyzer:
    """
    Service for analyzing subreddits.

    Gathers metadata, posting requirements, and optimal timing information.
    """

    def __init__(self):
        self.reddit = RedditClientFactory.create_read_only_client()

    def analyze_subreddit(
        self,
        db: Session,
        subreddit_name: str,
        project_id: int
    ) -> SubredditConfig:
        """
        Analyze a subreddit and create/update its config.

        Args:
            db: Database session
            subreddit_name: Name of subreddit
            project_id: Project ID to associate with

        Returns:
            SubredditConfig object
        """
        # Check for existing config
        config = db.query(SubredditConfig).filter(
            SubredditConfig.project_id == project_id,
            SubredditConfig.subreddit_name == subreddit_name
        ).first()

        if not config:
            config = SubredditConfig(
                project_id=project_id,
                subreddit_name=subreddit_name
            )
            db.add(config)

        try:
            # Fetch subreddit info
            subreddit = self.reddit.subreddit(subreddit_name)

            # Basic metadata
            config.subscribers = subreddit.subscribers
            config.active_users = subreddit.accounts_active
            config.subreddit_type = subreddit.subreddit_type

            # Calculate velocity threshold
            config.velocity_threshold = get_velocity_threshold(subreddit.subscribers)

            # Analyze posting requirements
            requirements = self._analyze_requirements(subreddit)
            config.min_account_age_days = requirements.get("min_account_age_days")
            config.min_karma = requirements.get("min_karma")
            config.min_comment_karma = requirements.get("min_comment_karma")
            config.allowed_content_types = requirements.get("allowed_content_types")

            # Analyze rules
            rules_summary = self._summarize_rules(subreddit)
            config.posting_rules = rules_summary
            config.rules_summary = rules_summary[:500] if rules_summary else None

            # Analyze timing
            timing = self._analyze_timing(subreddit)
            config.best_posting_hours = timing.get("best_hours")
            config.best_posting_days = timing.get("best_days")

            # Calculate averages
            config.avg_post_score = self._calculate_avg_post_score(subreddit)

            config.last_analyzed_at = datetime.utcnow()

            db.commit()
            logger.info(f"Analyzed r/{subreddit_name}: {config.subscribers} subscribers")

        except Exception as e:
            logger.error(f"Error analyzing r/{subreddit_name}: {e}")
            db.rollback()

        return config

    def _analyze_requirements(self, subreddit: praw.models.Subreddit) -> Dict[str, Any]:
        """
        Analyze posting requirements from subreddit rules.

        Returns dict with min_account_age_days, min_karma, etc.
        """
        requirements = {
            "min_account_age_days": None,
            "min_karma": None,
            "min_comment_karma": None,
            "allowed_content_types": ["text", "link"],
        }

        try:
            # Check subreddit settings
            if hasattr(subreddit, 'submission_type'):
                sub_type = subreddit.submission_type
                if sub_type == 'self':
                    requirements["allowed_content_types"] = ["text"]
                elif sub_type == 'link':
                    requirements["allowed_content_types"] = ["link"]

            # Parse rules for requirements
            for rule in subreddit.rules():
                rule_text = f"{rule.short_name} {rule.description}".lower()

                # Look for account age requirements
                if "day" in rule_text and ("account" in rule_text or "old" in rule_text):
                    # Try to extract number
                    import re
                    age_match = re.search(r'(\d+)\s*day', rule_text)
                    if age_match:
                        requirements["min_account_age_days"] = int(age_match.group(1))

                # Look for karma requirements
                if "karma" in rule_text:
                    karma_match = re.search(r'(\d+)\s*karma', rule_text)
                    if karma_match:
                        if "comment" in rule_text:
                            requirements["min_comment_karma"] = int(karma_match.group(1))
                        else:
                            requirements["min_karma"] = int(karma_match.group(1))

        except Exception as e:
            logger.warning(f"Error parsing requirements: {e}")

        return requirements

    def _summarize_rules(self, subreddit: praw.models.Subreddit) -> Optional[str]:
        """
        Summarize subreddit rules.

        Returns string summary of key rules.
        """
        try:
            rules = list(subreddit.rules())

            if not rules:
                return None

            summary_parts = []
            for rule in rules[:10]:  # Limit to first 10 rules
                summary_parts.append(f"- {rule.short_name}: {rule.description[:200]}")

            return "\n".join(summary_parts)

        except Exception as e:
            logger.warning(f"Error summarizing rules: {e}")
            return None

    def _analyze_timing(self, subreddit: praw.models.Subreddit) -> Dict[str, List[int]]:
        """
        Analyze optimal posting times.

        Returns dict with best_hours and best_days.
        """
        timing = {
            "best_hours": [],
            "best_days": [],
        }

        try:
            # Analyze top posts from past week
            hour_scores = {}
            day_scores = {}

            for submission in subreddit.top(time_filter="week", limit=100):
                created = datetime.utcfromtimestamp(submission.created_utc)
                hour = created.hour
                day = created.weekday()

                # Accumulate scores
                hour_scores[hour] = hour_scores.get(hour, 0) + submission.score
                day_scores[day] = day_scores.get(day, 0) + submission.score

            # Find best hours (top 5)
            if hour_scores:
                sorted_hours = sorted(hour_scores.items(), key=lambda x: x[1], reverse=True)
                timing["best_hours"] = [h for h, _ in sorted_hours[:5]]

            # Find best days
            if day_scores:
                sorted_days = sorted(day_scores.items(), key=lambda x: x[1], reverse=True)
                timing["best_days"] = [d for d, _ in sorted_days[:3]]

        except Exception as e:
            logger.warning(f"Error analyzing timing: {e}")
            # Default to common good times
            timing["best_hours"] = [14, 15, 16, 17, 18]  # 2-6 PM UTC
            timing["best_days"] = [0, 1, 2]  # Mon-Wed

        return timing

    def _calculate_avg_post_score(self, subreddit: praw.models.Subreddit) -> Optional[float]:
        """Calculate average post score for subreddit."""
        try:
            scores = []
            for submission in subreddit.hot(limit=50):
                scores.append(submission.score)

            if scores:
                return sum(scores) / len(scores)

        except Exception as e:
            logger.warning(f"Error calculating avg score: {e}")

        return None

    def batch_analyze(
        self,
        db: Session,
        subreddit_names: List[str],
        project_id: int
    ) -> List[SubredditConfig]:
        """
        Analyze multiple subreddits.

        Args:
            db: Database session
            subreddit_names: List of subreddit names
            project_id: Project ID

        Returns:
            List of SubredditConfig objects
        """
        configs = []

        for name in subreddit_names:
            try:
                config = self.analyze_subreddit(db, name, project_id)
                configs.append(config)
            except Exception as e:
                logger.error(f"Error analyzing r/{name}: {e}")
                continue

        return configs

    def get_posting_recommendation(
        self,
        config: SubredditConfig
    ) -> Dict[str, Any]:
        """
        Get posting recommendations for a subreddit.

        Args:
            config: SubredditConfig object

        Returns:
            Dict with recommendations
        """
        recommendations = {
            "can_post": True,
            "issues": [],
            "suggestions": [],
        }

        # Check requirements
        if config.min_account_age_days:
            recommendations["suggestions"].append(
                f"Account must be at least {config.min_account_age_days} days old"
            )

        if config.min_karma:
            recommendations["suggestions"].append(
                f"Account needs at least {config.min_karma} karma"
            )

        # Timing recommendations
        if config.best_posting_hours:
            hours_str = ", ".join(f"{h}:00 UTC" for h in config.best_posting_hours[:3])
            recommendations["suggestions"].append(
                f"Best posting times: {hours_str}"
            )

        if config.best_posting_days:
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            days_str = ", ".join(day_names[d] for d in config.best_posting_days)
            recommendations["suggestions"].append(
                f"Best posting days: {days_str}"
            )

        # Velocity info
        if config.velocity_threshold:
            recommendations["velocity_threshold"] = config.velocity_threshold
            recommendations["suggestions"].append(
                f"Target posts with velocity > {config.velocity_threshold:.1f}"
            )

        return recommendations
