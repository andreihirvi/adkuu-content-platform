"""
Celery tasks for opportunity mining.
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from celery import shared_task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.db.database import SessionLocal
from app.models import Project, ProjectStatus, Opportunity
from app.services.opportunity_miner import OpportunityMiner

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.mine_opportunities",
    max_retries=3,
    default_retry_delay=60,
    queue="opportunity-mining",
)
def mine_opportunities_task(self, project_id: int, subreddits: Optional[List[str]] = None, limit: int = 50):
    """
    Mine opportunities for a specific project.

    Args:
        project_id: Project ID to mine for
        subreddits: Optional list of subreddits (uses project defaults if not provided)
        limit: Maximum opportunities per subreddit
    """
    db = SessionLocal()

    try:
        project = db.query(Project).get(project_id)

        if not project:
            logger.error(f"Project {project_id} not found")
            return {"error": "Project not found"}

        if project.status != ProjectStatus.ACTIVE.value:
            logger.info(f"Project {project_id} is not active, skipping mining")
            return {"skipped": True, "reason": "Project not active"}

        # Get target subreddits
        target_subreddits = subreddits or project.target_subreddits

        if not target_subreddits:
            logger.warning(f"Project {project_id} has no target subreddits")
            return {"error": "No target subreddits configured"}

        logger.info(f"Starting mining for project {project_id} in {len(target_subreddits)} subreddits")

        miner = OpportunityMiner()
        opportunities = miner.mine_opportunities(
            db=db,
            project=project,
            subreddits=target_subreddits,
            limit=limit
        )

        logger.info(f"Found {len(opportunities)} opportunities for project {project_id}")

        return {
            "project_id": project_id,
            "opportunities_found": len(opportunities),
            "subreddits_mined": len(target_subreddits),
        }

    except Exception as e:
        logger.exception(f"Mining failed for project {project_id}: {e}")
        self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(
    name="tasks.scheduled_mining",
    queue="opportunity-mining",
)
def scheduled_mining_task():
    """
    Scheduled task to mine opportunities for all active projects.

    Runs every 15 minutes via Celery beat.
    """
    db = SessionLocal()

    try:
        # Get all active projects
        active_projects = db.query(Project).filter(
            Project.status == ProjectStatus.ACTIVE.value
        ).all()

        logger.info(f"Running scheduled mining for {len(active_projects)} active projects")

        results = []

        for project in active_projects:
            # Check automation level - only auto-mine for level 2+
            if project.automation_level < 2:
                continue

            try:
                # Queue individual mining task
                mine_opportunities_task.delay(project.id)
                results.append({"project_id": project.id, "queued": True})

            except Exception as e:
                logger.error(f"Failed to queue mining for project {project.id}: {e}")
                results.append({"project_id": project.id, "error": str(e)})

        return {
            "projects_queued": len([r for r in results if r.get("queued")]),
            "total_active": len(active_projects),
        }

    except Exception as e:
        logger.exception(f"Scheduled mining failed: {e}")
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(
    name="tasks.expire_opportunities",
    queue="opportunity-mining",
)
def expire_opportunities_task():
    """
    Mark old opportunities as expired.

    Opportunities are expired based on their urgency:
    - URGENT: expires after 30 min
    - HIGH: expires after 2 hours
    - MEDIUM: expires after 4 hours
    - LOW: expires after 24 hours
    """
    db = SessionLocal()

    try:
        now = datetime.utcnow()
        expired_count = 0

        # Get pending opportunities with expiration
        pending = db.query(Opportunity).filter(
            Opportunity.status == "pending",
            Opportunity.expires_at.isnot(None),
            Opportunity.expires_at < now
        ).all()

        for opp in pending:
            opp.status = "expired"
            expired_count += 1

        db.commit()

        logger.info(f"Expired {expired_count} opportunities")

        return {"expired_count": expired_count}

    except Exception as e:
        logger.exception(f"Expire task failed: {e}")
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(
    name="tasks.refresh_opportunity_scores",
    queue="opportunity-mining",
)
def refresh_opportunity_scores_task(opportunity_ids: Optional[List[int]] = None):
    """
    Refresh scores for pending opportunities.

    Re-fetches post data and recalculates velocity/timing scores.

    Args:
        opportunity_ids: Specific opportunities to refresh (all pending if None)
    """
    db = SessionLocal()

    try:
        query = db.query(Opportunity).filter(
            Opportunity.status == "pending"
        )

        if opportunity_ids:
            query = query.filter(Opportunity.id.in_(opportunity_ids))

        opportunities = query.limit(100).all()

        logger.info(f"Refreshing scores for {len(opportunities)} opportunities")

        miner = OpportunityMiner()
        refreshed = 0

        for opp in opportunities:
            try:
                miner.refresh_opportunity_scores(db, opp)
                refreshed += 1
            except Exception as e:
                logger.warning(f"Failed to refresh opportunity {opp.id}: {e}")

        return {"refreshed_count": refreshed}

    except Exception as e:
        logger.exception(f"Refresh scores task failed: {e}")
        return {"error": str(e)}

    finally:
        db.close()
