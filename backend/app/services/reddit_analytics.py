"""
Reddit Analytics Service - collects performance metrics for published content.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import praw
from sqlalchemy.orm import Session

from app.models import GeneratedContent, ContentPerformance, RedditAccount
from app.utils.reddit_helpers import RedditClientFactory, check_comment_removed, extract_comment_metrics

logger = logging.getLogger(__name__)


class RedditAnalyticsService:
    """
    Service for collecting Reddit analytics.

    Tracks:
    - Comment scores and engagement
    - Removal detection
    - Performance over time
    """

    def __init__(self):
        self.reddit = RedditClientFactory.create_read_only_client()

    def fetch_content_metrics(
        self,
        db: Session,
        content: GeneratedContent
    ) -> Optional[ContentPerformance]:
        """
        Fetch current metrics for published content.

        Args:
            db: Database session
            content: Published content to fetch metrics for

        Returns:
            ContentPerformance snapshot
        """
        if not content.published_reddit_id:
            logger.warning(f"Content {content.id} has no published Reddit ID")
            return None

        try:
            comment = self.reddit.comment(id=content.published_reddit_id)
            comment._fetch()

            # Extract metrics
            metrics = extract_comment_metrics(comment)

            # Check if removed
            is_removed = False
            removal_reason = None

            if comment.body in ["[removed]", "[deleted]"]:
                is_removed = True
                removal_reason = "removed" if comment.body == "[removed]" else "deleted"
            elif comment.author is None:
                is_removed = True
                removal_reason = "author_deleted"

            # Calculate engagement rate
            # Based on score relative to parent post engagement
            engagement_rate = None
            try:
                submission = comment.submission
                if submission.num_comments > 0:
                    engagement_rate = (metrics["score"] + metrics["num_replies"]) / max(submission.num_comments, 1)
            except Exception:
                pass

            # Calculate velocity (score change since last snapshot)
            velocity = None
            last_snapshot = db.query(ContentPerformance).filter(
                ContentPerformance.content_id == content.id
            ).order_by(ContentPerformance.snapshot_at.desc()).first()

            if last_snapshot:
                time_diff = (datetime.utcnow() - last_snapshot.snapshot_at).total_seconds() / 3600
                if time_diff > 0:
                    velocity = (metrics["score"] - last_snapshot.score) / time_diff

            # Create performance snapshot
            performance = ContentPerformance(
                content_id=content.id,
                snapshot_at=datetime.utcnow(),
                score=metrics["score"],
                upvotes=metrics["ups"],
                downvotes=metrics["downs"],
                num_replies=metrics["num_replies"],
                engagement_rate=engagement_rate,
                velocity=velocity,
                is_removed=is_removed,
                removal_reason=removal_reason,
                platform_metrics={
                    "controversiality": metrics.get("controversiality"),
                    "depth": metrics.get("depth"),
                    "is_submitter": metrics.get("is_submitter"),
                    "edited": metrics.get("edited"),
                }
            )

            db.add(performance)
            db.commit()

            # If removed, update content status and account removal rate
            if is_removed:
                self._handle_removal(db, content)

            return performance

        except Exception as e:
            logger.error(f"Error fetching metrics for content {content.id}: {e}")
            return None

    def batch_fetch_metrics(
        self,
        db: Session,
        contents: List[GeneratedContent]
    ) -> List[ContentPerformance]:
        """
        Batch fetch metrics for multiple contents.

        Args:
            db: Database session
            contents: List of published contents

        Returns:
            List of ContentPerformance snapshots
        """
        performances = []

        for content in contents:
            try:
                perf = self.fetch_content_metrics(db, content)
                if perf:
                    performances.append(perf)
            except Exception as e:
                logger.error(f"Error in batch fetch for content {content.id}: {e}")
                continue

        return performances

    def _handle_removal(self, db: Session, content: GeneratedContent):
        """Handle content removal - update stats."""
        # Update content status
        content.status = "deleted"

        # Update account removal rate if we know which account
        if content.reddit_account_id:
            account = db.query(RedditAccount).get(content.reddit_account_id)
            if account:
                account.total_posts_removed += 1
                if account.total_posts_made > 0:
                    account.removal_rate = account.total_posts_removed / account.total_posts_made

        db.commit()

    def get_content_performance_summary(
        self,
        db: Session,
        content_id: int
    ) -> Dict[str, Any]:
        """
        Get performance summary for a content.

        Args:
            db: Database session
            content_id: Content ID

        Returns:
            Dict with performance summary
        """
        snapshots = db.query(ContentPerformance).filter(
            ContentPerformance.content_id == content_id
        ).order_by(ContentPerformance.snapshot_at.asc()).all()

        if not snapshots:
            return {
                "content_id": content_id,
                "has_data": False,
            }

        latest = snapshots[-1]
        first = snapshots[0]

        # Calculate growth
        score_growth = latest.score - first.score if len(snapshots) > 1 else 0
        time_span_hours = (latest.snapshot_at - first.snapshot_at).total_seconds() / 3600 if len(snapshots) > 1 else 0

        return {
            "content_id": content_id,
            "has_data": True,
            "current_score": latest.score,
            "current_replies": latest.num_replies,
            "is_removed": latest.is_removed,
            "removal_reason": latest.removal_reason,
            "score_growth": score_growth,
            "time_span_hours": time_span_hours,
            "avg_velocity": score_growth / time_span_hours if time_span_hours > 0 else 0,
            "snapshot_count": len(snapshots),
            "first_snapshot": first.snapshot_at.isoformat(),
            "latest_snapshot": latest.snapshot_at.isoformat(),
        }

    def calculate_project_metrics(
        self,
        db: Session,
        project_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate aggregate metrics for a project.

        Args:
            db: Database session
            project_id: Project ID
            days: Number of days to analyze

        Returns:
            Dict with aggregate metrics
        """
        from datetime import timedelta
        from sqlalchemy import func

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get all published content for project
        contents = db.query(GeneratedContent).filter(
            GeneratedContent.project_id == project_id,
            GeneratedContent.status == "published",
            GeneratedContent.published_at >= cutoff
        ).all()

        if not contents:
            return {
                "project_id": project_id,
                "period_days": days,
                "total_published": 0,
            }

        # Get latest metrics for each content
        total_score = 0
        total_replies = 0
        removed_count = 0

        for content in contents:
            latest = db.query(ContentPerformance).filter(
                ContentPerformance.content_id == content.id
            ).order_by(ContentPerformance.snapshot_at.desc()).first()

            if latest:
                total_score += latest.score
                total_replies += latest.num_replies
                if latest.is_removed:
                    removed_count += 1

        avg_score = total_score / len(contents) if contents else 0
        removal_rate = removed_count / len(contents) if contents else 0

        return {
            "project_id": project_id,
            "period_days": days,
            "total_published": len(contents),
            "total_score": total_score,
            "total_replies": total_replies,
            "avg_score": avg_score,
            "removed_count": removed_count,
            "removal_rate": removal_rate,
        }

    def get_subreddit_performance(
        self,
        db: Session,
        project_id: int,
        subreddit: str
    ) -> Dict[str, Any]:
        """
        Get performance metrics for a specific subreddit.

        Args:
            db: Database session
            project_id: Project ID
            subreddit: Subreddit name

        Returns:
            Dict with subreddit performance
        """
        from app.models import Opportunity

        # Get opportunities and content for this subreddit
        opportunities = db.query(Opportunity).filter(
            Opportunity.project_id == project_id,
            Opportunity.subreddit == subreddit
        ).all()

        published_contents = []
        for opp in opportunities:
            contents = db.query(GeneratedContent).filter(
                GeneratedContent.opportunity_id == opp.id,
                GeneratedContent.status == "published"
            ).all()
            published_contents.extend(contents)

        if not published_contents:
            return {
                "subreddit": subreddit,
                "total_posts": 0,
            }

        # Aggregate metrics
        scores = []
        removal_count = 0

        for content in published_contents:
            latest = db.query(ContentPerformance).filter(
                ContentPerformance.content_id == content.id
            ).order_by(ContentPerformance.snapshot_at.desc()).first()

            if latest:
                scores.append(latest.score)
                if latest.is_removed:
                    removal_count += 1

        return {
            "subreddit": subreddit,
            "total_posts": len(published_contents),
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "removal_count": removal_count,
            "removal_rate": removal_count / len(published_contents) if published_contents else 0,
        }
