"""
Opportunity API endpoints.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.deps import get_db
from app.models import Opportunity, OpportunityStatus, Project, GeneratedContent
from app.schemas.opportunity import (
    OpportunityResponse,
    OpportunityDetailResponse,
    OpportunityListResponse,
    MiningRequest,
    MiningResult,
    ApproveRejectRequest,
)
from app.services.opportunity_miner import OpportunityMiner
from app.services.content_generator import ContentGenerator
from app.services.quality_gates import QualityGates

router = APIRouter()


@router.get("/", response_model=OpportunityListResponse)
async def list_opportunities(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    subreddit: Optional[str] = None,
    min_score: Optional[float] = None,
    urgency: Optional[str] = None,
    include_expired: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List opportunities with filtering."""
    query = db.query(Opportunity)

    if project_id:
        query = query.filter(Opportunity.project_id == project_id)

    if status:
        query = query.filter(Opportunity.status == status)
    elif not include_expired:
        query = query.filter(Opportunity.status != OpportunityStatus.EXPIRED.value)

    if subreddit:
        query = query.filter(Opportunity.subreddit == subreddit)

    if min_score is not None:
        query = query.filter(Opportunity.composite_score >= min_score)

    if urgency:
        query = query.filter(Opportunity.urgency == urgency)

    total = query.count()

    opportunities = query.order_by(
        desc(Opportunity.composite_score)
    ).offset(skip).limit(limit).all()

    return OpportunityListResponse(
        items=opportunities,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{opportunity_id}", response_model=OpportunityDetailResponse)
async def get_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
):
    """Get opportunity details."""
    opportunity = db.query(Opportunity).get(opportunity_id)

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Get content info
    contents = db.query(GeneratedContent).filter(
        GeneratedContent.opportunity_id == opportunity_id
    ).order_by(desc(GeneratedContent.created_at)).all()

    latest_content = contents[0] if contents else None

    return OpportunityDetailResponse(
        **opportunity.__dict__,
        generated_content_count=len(contents),
        latest_content_id=latest_content.id if latest_content else None,
        latest_content_status=latest_content.status if latest_content else None,
    )


@router.post("/{opportunity_id}/approve")
async def approve_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
):
    """Approve an opportunity for content generation."""
    opportunity = db.query(Opportunity).get(opportunity_id)

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if opportunity.status not in [OpportunityStatus.PENDING.value]:
        raise HTTPException(status_code=400, detail=f"Cannot approve opportunity with status: {opportunity.status}")

    opportunity.status = OpportunityStatus.APPROVED.value
    opportunity.processed_at = datetime.utcnow()
    db.commit()

    return {"status": "approved", "opportunity_id": opportunity_id}


@router.post("/{opportunity_id}/reject")
async def reject_opportunity(
    opportunity_id: int,
    request: ApproveRejectRequest = None,
    db: Session = Depends(get_db),
):
    """Reject an opportunity."""
    opportunity = db.query(Opportunity).get(opportunity_id)

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opportunity.status = OpportunityStatus.REJECTED.value
    opportunity.processed_at = datetime.utcnow()

    if request and request.reason:
        opportunity.opportunity_metadata = {
            **opportunity.opportunity_metadata,
            "rejection_reason": request.reason
        }

    db.commit()

    return {"status": "rejected", "opportunity_id": opportunity_id}


@router.post("/{opportunity_id}/generate-content")
async def generate_content_for_opportunity(
    opportunity_id: int,
    style: str = "helpful_expert",
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """Generate content for an opportunity."""
    opportunity = db.query(Opportunity).get(opportunity_id)

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    project = db.query(Project).get(opportunity.project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update status
    opportunity.status = OpportunityStatus.GENERATING.value
    db.commit()

    try:
        # Generate content
        generator = ContentGenerator()
        content = await generator.generate_content(opportunity, project, style)

        # Run quality checks
        quality_gates = QualityGates()
        quality_result = quality_gates.run_all_checks(content, opportunity)

        content.quality_score = quality_result.overall_score
        content.quality_checks = quality_result.to_dict()
        content.passed_quality_gates = quality_result.passed

        # Update status based on quality
        if quality_result.passed:
            content.status = "pending"  # Ready for review
        else:
            content.status = "draft"  # Needs improvement

        db.add(content)

        # Update opportunity status
        opportunity.status = OpportunityStatus.READY.value

        db.commit()
        db.refresh(content)

        return {
            "status": "success",
            "content_id": content.id,
            "quality_score": quality_result.overall_score,
            "passed_quality_gates": quality_result.passed,
            "warnings": quality_result.warnings,
        }

    except Exception as e:
        opportunity.status = OpportunityStatus.PENDING.value
        db.commit()
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")


@router.post("/mine", response_model=MiningResult)
async def trigger_mining(
    request: MiningRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Manually trigger opportunity mining for a project."""
    project = db.query(Project).get(request.project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != "active":
        raise HTTPException(status_code=400, detail="Project is not active")

    # Mine synchronously for immediate feedback
    miner = OpportunityMiner()

    try:
        subreddits = request.subreddits or project.target_subreddits

        if not subreddits:
            raise HTTPException(status_code=400, detail="No target subreddits configured")

        opportunities = miner.mine_opportunities(
            db=db,
            project=project,
            subreddits=subreddits,
            limit=request.limit
        )

        return MiningResult(
            opportunities_found=len(opportunities),
            opportunities_new=len(opportunities),
            status="completed",
            message=f"Found {len(opportunities)} new opportunities"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mining failed: {str(e)}")


@router.post("/{opportunity_id}/refresh")
async def refresh_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
):
    """Refresh scores for an opportunity."""
    opportunity = db.query(Opportunity).get(opportunity_id)

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    miner = OpportunityMiner()
    opportunity = miner.refresh_opportunity_scores(db, opportunity)

    return OpportunityResponse.from_orm(opportunity)
