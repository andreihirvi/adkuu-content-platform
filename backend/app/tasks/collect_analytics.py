"""
Celery tasks for analytics collection and learning.
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from celery import shared_task
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.celery_app import celery_app
from app.db.database import SessionLocal
from app.models import (
    Project, GeneratedContent, ContentPerformance,
    ContentStatus, LearningFeature, Opportunity
)
from app.services.reddit_analytics import RedditAnalyticsService

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.collect_content_analytics",
    max_retries=3,
    default_retry_delay=60,
    queue="analytics",
)
def collect_content_analytics_task(self, content_id: int):
    """
    Collect analytics for a single piece of published content.

    Args:
        content_id: Content ID to collect analytics for
    """
    db = SessionLocal()

    try:
        content = db.query(GeneratedContent).get(content_id)

        if not content:
            logger.error(f"Content {content_id} not found")
            return {"error": "Content not found"}

        if content.status != ContentStatus.PUBLISHED.value:
            logger.info(f"Content {content_id} is not published, skipping")
            return {"skipped": True, "reason": "Not published"}

        if not content.published_reddit_id:
            logger.warning(f"Content {content_id} has no Reddit ID")
            return {"error": "No Reddit ID"}

        analytics_service = RedditAnalyticsService()

        # Determine content type (comment vs post)
        is_comment = content.content_type == "comment"

        # Fetch metrics
        metrics = analytics_service.fetch_content_metrics(
            db, content.published_reddit_id, is_comment=is_comment
        )

        if not metrics:
            logger.warning(f"Could not fetch metrics for content {content_id}")
            return {"error": "Metrics fetch failed"}

        # Create performance snapshot
        snapshot = ContentPerformance(
            content_id=content_id,
            score=metrics.get("score", 0),
            upvotes=metrics.get("ups", 0),
            downvotes=metrics.get("downs", 0),
            num_replies=metrics.get("num_replies", 0),
            is_removed=metrics.get("is_removed", False),
            removal_reason=metrics.get("removal_reason"),
            platform_metrics=metrics,
        )

        # Calculate velocity if we have previous snapshots
        prev_snapshot = db.query(ContentPerformance).filter(
            ContentPerformance.content_id == content_id
        ).order_by(ContentPerformance.snapshot_at.desc()).first()

        if prev_snapshot:
            hours_diff = (datetime.utcnow() - prev_snapshot.snapshot_at).total_seconds() / 3600
            if hours_diff > 0:
                score_diff = snapshot.score - prev_snapshot.score
                snapshot.velocity = score_diff / hours_diff

        db.add(snapshot)
        db.commit()

        logger.info(
            f"Collected analytics for content {content_id}: "
            f"score={snapshot.score}, replies={snapshot.num_replies}, removed={snapshot.is_removed}"
        )

        return {
            "content_id": content_id,
            "score": snapshot.score,
            "num_replies": snapshot.num_replies,
            "is_removed": snapshot.is_removed,
        }

    except Exception as e:
        logger.exception(f"Analytics collection failed for content {content_id}: {e}")
        self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(
    name="tasks.collect_all_analytics",
    queue="analytics",
)
def collect_all_analytics_task():
    """
    Collect analytics for all recently published content.

    Runs periodically to update performance metrics.
    """
    db = SessionLocal()

    try:
        # Get content published in the last 7 days that isn't removed
        cutoff = datetime.utcnow() - timedelta(days=7)

        contents = db.query(GeneratedContent).filter(
            GeneratedContent.status == ContentStatus.PUBLISHED.value,
            GeneratedContent.published_at >= cutoff,
            GeneratedContent.published_reddit_id.isnot(None)
        ).all()

        logger.info(f"Collecting analytics for {len(contents)} published items")

        queued = 0

        for content in contents:
            try:
                collect_content_analytics_task.delay(content.id)
                queued += 1
            except Exception as e:
                logger.error(f"Failed to queue analytics for content {content.id}: {e}")

        return {"queued_count": queued}

    except Exception as e:
        logger.exception(f"Collect all analytics task failed: {e}")
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(
    name="tasks.update_learning_features",
    queue="analytics",
)
def update_learning_features_task(project_id: Optional[int] = None):
    """
    Update learning features based on content performance.

    Analyzes successful vs unsuccessful content to extract patterns.

    Args:
        project_id: Optional project to update (all if None)
    """
    db = SessionLocal()

    try:
        # Get performance data for learning
        query = db.query(GeneratedContent).filter(
            GeneratedContent.status == ContentStatus.PUBLISHED.value,
            GeneratedContent.published_at.isnot(None)
        )

        if project_id:
            query = query.filter(GeneratedContent.project_id == project_id)

        contents = query.all()

        logger.info(f"Updating learning features from {len(contents)} published items")

        # Aggregate features
        features_data = {}

        for content in contents:
            # Get latest performance
            perf = db.query(ContentPerformance).filter(
                ContentPerformance.content_id == content.id
            ).order_by(ContentPerformance.snapshot_at.desc()).first()

            if not perf:
                continue

            # Define success (score > 5 and not removed)
            is_success = perf.score >= 5 and not perf.is_removed

            # Get opportunity for context
            opportunity = None
            if content.opportunity_id:
                opportunity = db.query(Opportunity).get(content.opportunity_id)

            # Extract timing features (hour of day)
            if content.published_at:
                hour = content.published_at.hour
                key = ("timing", str(hour), content.project_id)

                if key not in features_data:
                    features_data[key] = {"successes": 0, "samples": 0, "scores": []}

                features_data[key]["samples"] += 1
                features_data[key]["scores"].append(perf.score)
                if is_success:
                    features_data[key]["successes"] += 1

            # Extract subreddit features
            if opportunity and opportunity.subreddit:
                key = ("subreddit", opportunity.subreddit, content.project_id)

                if key not in features_data:
                    features_data[key] = {"successes": 0, "samples": 0, "scores": []}

                features_data[key]["samples"] += 1
                features_data[key]["scores"].append(perf.score)
                if is_success:
                    features_data[key]["successes"] += 1

            # Extract style features
            if content.style:
                key = ("style", content.style, content.project_id)

                if key not in features_data:
                    features_data[key] = {"successes": 0, "samples": 0, "scores": []}

                features_data[key]["samples"] += 1
                features_data[key]["scores"].append(perf.score)
                if is_success:
                    features_data[key]["successes"] += 1

        # Update or create learning features
        updated = 0

        for (feature_type, feature_key, proj_id), data in features_data.items():
            if data["samples"] < 3:  # Need minimum samples
                continue

            feature = db.query(LearningFeature).filter(
                LearningFeature.feature_type == feature_type,
                LearningFeature.feature_key == feature_key,
                LearningFeature.project_id == proj_id
            ).first()

            success_rate = data["successes"] / data["samples"]
            avg_score = sum(data["scores"]) / len(data["scores"])

            if feature:
                feature.sample_count = data["samples"]
                feature.success_rate = success_rate
                feature.avg_score = avg_score
                feature.last_updated_at = datetime.utcnow()
            else:
                feature = LearningFeature(
                    feature_type=feature_type,
                    feature_key=feature_key,
                    project_id=proj_id,
                    sample_count=data["samples"],
                    success_rate=success_rate,
                    avg_score=avg_score,
                )
                db.add(feature)

            updated += 1

        db.commit()

        logger.info(f"Updated {updated} learning features")

        return {"updated_features": updated}

    except Exception as e:
        logger.exception(f"Learning features update failed: {e}")
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(
    name="tasks.calculate_project_metrics",
    queue="analytics",
)
def calculate_project_metrics_task(project_id: int, days: int = 30):
    """
    Calculate aggregate metrics for a project.

    Args:
        project_id: Project to calculate metrics for
        days: Number of days to include
    """
    db = SessionLocal()

    try:
        analytics_service = RedditAnalyticsService()
        metrics = analytics_service.calculate_project_metrics(db, project_id, days)

        logger.info(f"Calculated metrics for project {project_id}: {metrics}")

        return {
            "project_id": project_id,
            "days": days,
            "metrics": metrics,
        }

    except Exception as e:
        logger.exception(f"Project metrics calculation failed: {e}")
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(
    name="tasks.detect_removals",
    queue="analytics",
)
def detect_removals_task():
    """
    Detect content that has been removed by moderators.

    Scans published content and updates removal status.
    """
    db = SessionLocal()

    try:
        # Get published content from last 30 days without recent checks
        cutoff = datetime.utcnow() - timedelta(days=30)

        contents = db.query(GeneratedContent).filter(
            GeneratedContent.status == ContentStatus.PUBLISHED.value,
            GeneratedContent.published_at >= cutoff,
            GeneratedContent.published_reddit_id.isnot(None)
        ).all()

        analytics_service = RedditAnalyticsService()
        removed_count = 0

        for content in contents:
            try:
                is_comment = content.content_type == "comment"
                metrics = analytics_service.fetch_content_metrics(
                    db, content.published_reddit_id, is_comment=is_comment
                )

                if metrics and metrics.get("is_removed"):
                    # Update latest performance snapshot
                    latest_perf = db.query(ContentPerformance).filter(
                        ContentPerformance.content_id == content.id
                    ).order_by(ContentPerformance.snapshot_at.desc()).first()

                    if latest_perf and not latest_perf.is_removed:
                        latest_perf.is_removed = True
                        latest_perf.removal_reason = metrics.get("removal_reason")
                        removed_count += 1

            except Exception as e:
                logger.warning(f"Failed to check removal for content {content.id}: {e}")

        db.commit()

        logger.info(f"Detected {removed_count} removed items")

        return {"removed_count": removed_count}

    except Exception as e:
        logger.exception(f"Removal detection failed: {e}")
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()
