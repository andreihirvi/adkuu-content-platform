"""
Opportunity Mining Service - discovers and scores Reddit opportunities.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set
import praw
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Opportunity, OpportunityStatus, OpportunityUrgency, Project, SubredditConfig
from app.services.virality_predictor import ViralityPredictor
from app.utils.reddit_helpers import (
    RedditClientFactory,
    calculate_post_velocity,
    get_post_age_hours,
    classify_urgency,
    get_velocity_threshold,
    extract_submission_data,
    get_rising_posts,
)

logger = logging.getLogger(__name__)


class OpportunityMiner:
    """
    Service for mining Reddit opportunities.

    Discovers rising posts that match project keywords and scores them
    based on relevance, virality potential, and timing.
    """

    # Scoring weights
    WEIGHT_RELEVANCE = 0.30
    WEIGHT_VIRALITY = 0.25
    WEIGHT_TIMING = 0.40
    WEIGHT_EFFORT = 0.05

    def __init__(self):
        self.reddit = RedditClientFactory.create_read_only_client()
        self.virality_predictor = ViralityPredictor()

    def mine_opportunities(
        self,
        db: Session,
        project: Project,
        subreddits: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Opportunity]:
        """
        Mine opportunities for a project.

        Args:
            db: Database session
            project: Project to mine for
            subreddits: Optional list of subreddits (defaults to project's)
            limit: Maximum posts to process

        Returns:
            List of new Opportunity objects
        """
        target_subreddits = subreddits or project.target_subreddits

        if not target_subreddits:
            logger.warning(f"Project {project.id} has no target subreddits")
            return []

        # Get existing reddit post IDs to avoid duplicates
        existing_ids = self._get_existing_post_ids(db, project.id)

        # Get subreddit configs for velocity thresholds
        subreddit_configs = self._get_subreddit_configs(db, project.id)

        opportunities = []
        processed_count = 0

        for subreddit_name in target_subreddits:
            if processed_count >= limit:
                break

            try:
                subreddit_opps = self._mine_subreddit(
                    db=db,
                    project=project,
                    subreddit_name=subreddit_name,
                    existing_ids=existing_ids,
                    subreddit_config=subreddit_configs.get(subreddit_name),
                    limit=min(50, limit - processed_count)
                )

                opportunities.extend(subreddit_opps)
                processed_count += len(subreddit_opps)

            except Exception as e:
                logger.error(f"Error mining r/{subreddit_name}: {e}")
                continue

        # Save to database
        if opportunities:
            db.add_all(opportunities)
            db.commit()
            logger.info(f"Mined {len(opportunities)} opportunities for project {project.id}")

        return opportunities

    def _mine_subreddit(
        self,
        db: Session,
        project: Project,
        subreddit_name: str,
        existing_ids: Set[str],
        subreddit_config: Optional[SubredditConfig],
        limit: int
    ) -> List[Opportunity]:
        """Mine opportunities from a single subreddit."""
        opportunities = []

        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            # Get velocity threshold
            if subreddit_config and subreddit_config.velocity_threshold:
                velocity_threshold = subreddit_config.velocity_threshold
            else:
                velocity_threshold = get_velocity_threshold(subreddit.subscribers)

            # Get rising and new posts
            posts_to_check = []

            for submission in subreddit.rising(limit=limit):
                posts_to_check.append(submission)

            for submission in subreddit.new(limit=limit // 2):
                if submission.id not in [p.id for p in posts_to_check]:
                    posts_to_check.append(submission)

            # Process each post
            for submission in posts_to_check:
                if submission.id in existing_ids:
                    continue

                # Skip old posts (> 24 hours)
                age_hours = get_post_age_hours(submission)
                if age_hours > 24:
                    continue

                # Calculate scores
                relevance_score = self._calculate_relevance(submission, project)

                # Skip low relevance
                if relevance_score < 0.3:
                    continue

                # Calculate other scores
                velocity = calculate_post_velocity(submission)
                virality_score = self.virality_predictor.predict(submission, velocity_threshold)
                timing_score = self._calculate_timing_score(velocity, age_hours, velocity_threshold)

                # Classify urgency
                urgency = classify_urgency(velocity, age_hours, velocity_threshold)

                # Calculate composite score
                composite_score = self._calculate_composite_score(
                    relevance_score,
                    virality_score,
                    timing_score
                )

                # Create opportunity
                submission_data = extract_submission_data(submission)

                opportunity = Opportunity(
                    project_id=project.id,
                    reddit_post_id=submission.id,
                    subreddit=subreddit_name,
                    post_title=submission_data["post_title"],
                    post_content=submission_data["post_content"],
                    post_url=submission_data["post_url"],
                    post_author=submission_data["post_author"],
                    post_created_at=submission_data["post_created_at"],
                    post_score=submission_data["post_score"],
                    post_num_comments=submission_data["post_num_comments"],
                    post_upvote_ratio=submission_data["post_upvote_ratio"],
                    relevance_score=relevance_score,
                    virality_score=virality_score,
                    timing_score=timing_score,
                    composite_score=composite_score,
                    urgency=urgency,
                    velocity=velocity,
                    velocity_threshold=velocity_threshold,
                    status=OpportunityStatus.PENDING.value,
                    expires_at=self._calculate_expiry(age_hours, urgency),
                    opportunity_metadata={
                        "is_self": submission_data["is_self"],
                        "link_flair_text": submission_data.get("link_flair_text"),
                        "over_18": submission_data.get("over_18", False),
                    }
                )

                opportunities.append(opportunity)
                existing_ids.add(submission.id)

        except Exception as e:
            logger.error(f"Error processing r/{subreddit_name}: {e}")

        return opportunities

    def _calculate_relevance(self, submission: praw.models.Submission, project: Project) -> float:
        """
        Calculate relevance score based on keyword matching.

        Args:
            submission: Reddit submission
            project: Project with keywords

        Returns:
            float: Relevance score (0-1)
        """
        if not project.keywords:
            return 0.5  # Default if no keywords

        # Combine title and content
        text = f"{submission.title} {submission.selftext if submission.is_self else ''}".lower()

        # Check positive keywords
        positive_matches = 0
        for keyword in project.keywords:
            if keyword.lower() in text:
                positive_matches += 1

        # Check negative keywords
        negative_matches = 0
        for keyword in project.negative_keywords or []:
            if keyword.lower() in text:
                negative_matches += 1

        # Calculate score
        if positive_matches == 0:
            return 0.0

        positive_score = min(positive_matches / len(project.keywords), 1.0)
        negative_penalty = negative_matches * 0.2

        return max(0.0, min(1.0, positive_score - negative_penalty))

    def _calculate_timing_score(
        self,
        velocity: float,
        age_hours: float,
        threshold: float
    ) -> float:
        """
        Calculate timing score based on velocity and age.

        Args:
            velocity: Post velocity
            age_hours: Post age in hours
            threshold: Velocity threshold for subreddit

        Returns:
            float: Timing score (0-1)
        """
        # Urgency-based scoring
        urgency = classify_urgency(velocity, age_hours, threshold)

        urgency_scores = {
            "urgent": 1.0,
            "high": 0.85,
            "medium": 0.6,
            "low": 0.3,
            "expired": 0.1,
        }

        return urgency_scores.get(urgency, 0.3)

    def _calculate_composite_score(
        self,
        relevance: float,
        virality: float,
        timing: float,
        effort: float = 0.5
    ) -> float:
        """Calculate weighted composite score."""
        return (
            relevance * self.WEIGHT_RELEVANCE +
            virality * self.WEIGHT_VIRALITY +
            timing * self.WEIGHT_TIMING +
            effort * self.WEIGHT_EFFORT
        )

    def _calculate_expiry(self, age_hours: float, urgency: str) -> datetime:
        """Calculate when opportunity expires."""
        # Expiry windows based on urgency
        windows = {
            "urgent": 1,      # 1 hour window
            "high": 2,        # 2 hour window
            "medium": 4,      # 4 hour window
            "low": 8,         # 8 hour window
            "expired": 0,
        }

        window_hours = windows.get(urgency, 4)
        remaining_hours = max(0, window_hours - age_hours)

        return datetime.utcnow() + timedelta(hours=remaining_hours)

    def _get_existing_post_ids(self, db: Session, project_id: int) -> Set[str]:
        """Get set of existing Reddit post IDs for project."""
        results = db.query(Opportunity.reddit_post_id).filter(
            Opportunity.project_id == project_id
        ).all()

        return {r[0] for r in results}

    def _get_subreddit_configs(self, db: Session, project_id: int) -> Dict[str, SubredditConfig]:
        """Get subreddit configs indexed by name."""
        configs = db.query(SubredditConfig).filter(
            SubredditConfig.project_id == project_id
        ).all()

        return {c.subreddit_name: c for c in configs}

    def refresh_opportunity_scores(
        self,
        db: Session,
        opportunity: Opportunity
    ) -> Opportunity:
        """
        Refresh scores for an existing opportunity.

        Args:
            db: Database session
            opportunity: Opportunity to refresh

        Returns:
            Updated Opportunity
        """
        try:
            submission = self.reddit.submission(id=opportunity.reddit_post_id)
            submission._fetch()

            # Recalculate velocity and timing
            age_hours = get_post_age_hours(submission)
            velocity = calculate_post_velocity(submission)

            opportunity.post_score = submission.score
            opportunity.post_num_comments = submission.num_comments
            opportunity.velocity = velocity

            # Recalculate timing score
            timing_score = self._calculate_timing_score(
                velocity,
                age_hours,
                opportunity.velocity_threshold or 15.0
            )
            opportunity.timing_score = timing_score

            # Recalculate urgency
            opportunity.urgency = classify_urgency(
                velocity,
                age_hours,
                opportunity.velocity_threshold or 15.0
            )

            # Recalculate composite
            opportunity.composite_score = self._calculate_composite_score(
                opportunity.relevance_score or 0.5,
                opportunity.virality_score or 0.5,
                timing_score
            )

            # Check if expired
            if opportunity.urgency == "expired" and opportunity.status == OpportunityStatus.PENDING.value:
                opportunity.status = OpportunityStatus.EXPIRED.value

            db.commit()

        except Exception as e:
            logger.error(f"Error refreshing opportunity {opportunity.id}: {e}")

        return opportunity
