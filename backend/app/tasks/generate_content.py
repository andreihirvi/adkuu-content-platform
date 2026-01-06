"""
Celery tasks for content generation.
"""
import logging
from typing import Optional

from celery import shared_task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.db.database import SessionLocal
from app.models import (
    Project, Opportunity, GeneratedContent,
    OpportunityStatus, ContentStatus
)
from app.services.content_generator import ContentGenerator
from app.services.quality_gates import QualityGates

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.generate_content",
    max_retries=2,
    default_retry_delay=30,
    queue="content-generation",
)
def generate_content_task(
    self,
    opportunity_id: int,
    style: str = "helpful_expert",
    auto_approve: bool = False,
):
    """
    Generate content for an opportunity.

    Args:
        opportunity_id: Opportunity to generate content for
        style: Content style (helpful_expert, casual, technical)
        auto_approve: If True and quality passes, auto-approve content
    """
    db = SessionLocal()

    try:
        opportunity = db.query(Opportunity).get(opportunity_id)

        if not opportunity:
            logger.error(f"Opportunity {opportunity_id} not found")
            return {"error": "Opportunity not found"}

        project = db.query(Project).get(opportunity.project_id)

        if not project:
            logger.error(f"Project not found for opportunity {opportunity_id}")
            return {"error": "Project not found"}

        # Update opportunity status
        opportunity.status = OpportunityStatus.GENERATING.value
        db.commit()

        logger.info(f"Generating content for opportunity {opportunity_id}")

        # Generate content
        generator = ContentGenerator()

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            content = loop.run_until_complete(
                generator.generate_content(opportunity, project, style)
            )
        finally:
            loop.close()

        # Run quality gates
        quality_gates = QualityGates()
        quality_result = quality_gates.run_all_checks(content, opportunity)

        content.quality_score = quality_result.overall_score
        content.quality_checks = quality_result.to_dict()
        content.passed_quality_gates = quality_result.passed

        # Set status based on quality and auto-approve
        if quality_result.passed:
            if auto_approve and project.automation_level >= 3:
                content.status = ContentStatus.APPROVED.value
            else:
                content.status = ContentStatus.PENDING.value
        else:
            content.status = ContentStatus.DRAFT.value

        # Update opportunity status
        opportunity.status = OpportunityStatus.READY.value

        db.add(content)
        db.commit()
        db.refresh(content)

        logger.info(
            f"Generated content {content.id} for opportunity {opportunity_id}, "
            f"quality: {quality_result.overall_score:.2f}, passed: {quality_result.passed}"
        )

        return {
            "content_id": content.id,
            "opportunity_id": opportunity_id,
            "quality_score": quality_result.overall_score,
            "passed_quality_gates": quality_result.passed,
            "status": content.status,
            "warnings": quality_result.warnings,
        }

    except Exception as e:
        logger.exception(f"Content generation failed for opportunity {opportunity_id}: {e}")

        # Reset opportunity status on failure
        if opportunity:
            opportunity.status = OpportunityStatus.PENDING.value
            db.commit()

        self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="tasks.regenerate_content",
    max_retries=2,
    default_retry_delay=30,
    queue="content-generation",
)
def regenerate_content_task(
    self,
    content_id: int,
    feedback: Optional[str] = None,
    new_style: Optional[str] = None,
):
    """
    Regenerate content with optional feedback.

    Args:
        content_id: Content to regenerate
        feedback: Optional feedback for improvement
        new_style: Optional new style to use
    """
    db = SessionLocal()

    try:
        content = db.query(GeneratedContent).get(content_id)

        if not content:
            logger.error(f"Content {content_id} not found")
            return {"error": "Content not found"}

        if content.status == ContentStatus.PUBLISHED.value:
            logger.error(f"Cannot regenerate published content {content_id}")
            return {"error": "Cannot regenerate published content"}

        opportunity = None
        if content.opportunity_id:
            opportunity = db.query(Opportunity).get(content.opportunity_id)

        project = db.query(Project).get(content.project_id)

        if not project:
            logger.error(f"Project not found for content {content_id}")
            return {"error": "Project not found"}

        logger.info(f"Regenerating content {content_id}")

        generator = ContentGenerator()

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            new_content = loop.run_until_complete(
                generator.regenerate_content(
                    content=content,
                    opportunity=opportunity,
                    project=project,
                    feedback=feedback,
                    new_style=new_style,
                )
            )
        finally:
            loop.close()

        # Run quality gates
        quality_gates = QualityGates()
        quality_result = quality_gates.run_all_checks(new_content, opportunity)

        new_content.quality_score = quality_result.overall_score
        new_content.quality_checks = quality_result.to_dict()
        new_content.passed_quality_gates = quality_result.passed

        if quality_result.passed:
            new_content.status = ContentStatus.PENDING.value
        else:
            new_content.status = ContentStatus.DRAFT.value

        db.add(new_content)
        db.commit()
        db.refresh(new_content)

        logger.info(
            f"Regenerated content {new_content.id} from {content_id}, "
            f"quality: {quality_result.overall_score:.2f}"
        )

        return {
            "new_content_id": new_content.id,
            "original_content_id": content_id,
            "quality_score": quality_result.overall_score,
            "passed_quality_gates": quality_result.passed,
            "version": new_content.version,
        }

    except Exception as e:
        logger.exception(f"Regeneration failed for content {content_id}: {e}")
        self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(
    name="tasks.batch_generate_content",
    queue="content-generation",
)
def batch_generate_content_task(project_id: int, max_items: int = 10):
    """
    Generate content for approved opportunities in batch.

    Args:
        project_id: Project to generate content for
        max_items: Maximum number of opportunities to process
    """
    db = SessionLocal()

    try:
        # Get approved opportunities without content
        opportunities = db.query(Opportunity).filter(
            Opportunity.project_id == project_id,
            Opportunity.status == OpportunityStatus.APPROVED.value
        ).order_by(
            Opportunity.composite_score.desc()
        ).limit(max_items).all()

        logger.info(
            f"Batch generating content for {len(opportunities)} opportunities "
            f"in project {project_id}"
        )

        queued = []

        for opp in opportunities:
            try:
                generate_content_task.delay(opp.id)
                queued.append(opp.id)
            except Exception as e:
                logger.error(f"Failed to queue content generation for opportunity {opp.id}: {e}")

        return {
            "project_id": project_id,
            "queued_count": len(queued),
            "opportunity_ids": queued,
        }

    except Exception as e:
        logger.exception(f"Batch generation failed for project {project_id}: {e}")
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(
    name="tasks.auto_generate_for_urgent",
    queue="content-generation",
)
def auto_generate_for_urgent_task():
    """
    Auto-generate content for urgent opportunities.

    For projects with automation_level >= 3, automatically generates
    content for URGENT opportunities.
    """
    db = SessionLocal()

    try:
        # Get urgent opportunities from high-automation projects
        urgent_opps = db.query(Opportunity).join(Project).filter(
            Project.automation_level >= 3,
            Opportunity.status == OpportunityStatus.PENDING.value,
            Opportunity.urgency == "urgent"
        ).all()

        logger.info(f"Auto-generating for {len(urgent_opps)} urgent opportunities")

        queued = []

        for opp in urgent_opps:
            try:
                # Auto-approve for urgent items in high automation
                generate_content_task.delay(opp.id, auto_approve=True)
                queued.append(opp.id)
            except Exception as e:
                logger.error(f"Failed to queue auto-generation for opportunity {opp.id}: {e}")

        return {
            "queued_count": len(queued),
            "opportunity_ids": queued,
        }

    except Exception as e:
        logger.exception(f"Auto-generate task failed: {e}")
        return {"error": str(e)}

    finally:
        db.close()
