"""
Content API endpoints.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.deps import get_db
from app.models import GeneratedContent, ContentStatus, Opportunity, Project, ContentPerformance
from app.schemas.content import (
    ContentUpdate,
    ContentResponse,
    ContentDetailResponse,
    ContentListResponse,
    GenerateContentRequest,
    PublishContentRequest,
    PublishResult,
    RegenerateRequest,
    PerformanceSnapshot,
    ContentPerformanceResponse,
)
from app.services.content_generator import ContentGenerator
from app.services.quality_gates import QualityGates
from app.services.reddit_publisher import RedditPublisher

router = APIRouter()


@router.get("/", response_model=ContentListResponse)
async def list_content(
    project_id: Optional[int] = None,
    opportunity_id: Optional[int] = None,
    status: Optional[str] = None,
    passed_quality: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List generated content with filtering."""
    query = db.query(GeneratedContent)

    if project_id:
        query = query.filter(GeneratedContent.project_id == project_id)

    if opportunity_id:
        query = query.filter(GeneratedContent.opportunity_id == opportunity_id)

    if status:
        query = query.filter(GeneratedContent.status == status)

    if passed_quality is not None:
        query = query.filter(GeneratedContent.passed_quality_gates == passed_quality)

    total = query.count()

    contents = query.order_by(
        desc(GeneratedContent.created_at)
    ).offset(skip).limit(limit).all()

    return ContentListResponse(
        items=contents,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{content_id}", response_model=ContentDetailResponse)
async def get_content(
    content_id: int,
    db: Session = Depends(get_db),
):
    """Get content details."""
    content = db.query(GeneratedContent).get(content_id)

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Get opportunity info
    opportunity = None
    if content.opportunity_id:
        opportunity = db.query(Opportunity).get(content.opportunity_id)

    # Get latest performance
    latest_perf = db.query(ContentPerformance).filter(
        ContentPerformance.content_id == content_id
    ).order_by(desc(ContentPerformance.snapshot_at)).first()

    return ContentDetailResponse(
        **content.__dict__,
        opportunity_title=opportunity.post_title if opportunity else None,
        opportunity_subreddit=opportunity.subreddit if opportunity else None,
        latest_score=latest_perf.score if latest_perf else None,
        latest_num_replies=latest_perf.num_replies if latest_perf else None,
        is_removed=latest_perf.is_removed if latest_perf else False,
    )


@router.put("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: int,
    content_in: ContentUpdate,
    db: Session = Depends(get_db),
):
    """Update content text (manual edit)."""
    content = db.query(GeneratedContent).get(content_id)

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    if content.status == ContentStatus.PUBLISHED.value:
        raise HTTPException(status_code=400, detail="Cannot edit published content")

    if content_in.content_text:
        content.content_text = content_in.content_text

        # Re-run quality checks
        quality_gates = QualityGates()
        opportunity = db.query(Opportunity).get(content.opportunity_id) if content.opportunity_id else None
        quality_result = quality_gates.run_all_checks(content, opportunity)

        content.quality_score = quality_result.overall_score
        content.quality_checks = quality_result.to_dict()
        content.passed_quality_gates = quality_result.passed

    if content_in.style:
        content.style = content_in.style

    db.commit()
    db.refresh(content)

    return content


@router.post("/{content_id}/regenerate", response_model=ContentResponse)
async def regenerate_content(
    content_id: int,
    request: RegenerateRequest = None,
    db: Session = Depends(get_db),
):
    """Regenerate content with optional feedback."""
    content = db.query(GeneratedContent).get(content_id)

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    if content.status == ContentStatus.PUBLISHED.value:
        raise HTTPException(status_code=400, detail="Cannot regenerate published content")

    opportunity = db.query(Opportunity).get(content.opportunity_id) if content.opportunity_id else None
    project = db.query(Project).get(content.project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        generator = ContentGenerator()
        new_content = await generator.regenerate_content(
            content=content,
            opportunity=opportunity,
            project=project,
            feedback=request.feedback if request else None,
            new_style=request.style if request else None,
        )

        # Run quality checks
        quality_gates = QualityGates()
        quality_result = quality_gates.run_all_checks(new_content, opportunity)

        new_content.quality_score = quality_result.overall_score
        new_content.quality_checks = quality_result.to_dict()
        new_content.passed_quality_gates = quality_result.passed

        if quality_result.passed:
            new_content.status = "pending"
        else:
            new_content.status = "draft"

        db.add(new_content)
        db.commit()
        db.refresh(new_content)

        return new_content

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")


@router.post("/{content_id}/approve")
async def approve_content(
    content_id: int,
    db: Session = Depends(get_db),
):
    """Approve content for publishing."""
    content = db.query(GeneratedContent).get(content_id)

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    if content.status not in ["draft", "pending"]:
        raise HTTPException(status_code=400, detail=f"Cannot approve content with status: {content.status}")

    content.status = ContentStatus.APPROVED.value
    db.commit()

    return {"status": "approved", "content_id": content_id}


@router.post("/{content_id}/reject")
async def reject_content(
    content_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Reject content."""
    content = db.query(GeneratedContent).get(content_id)

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    content.status = ContentStatus.REJECTED.value
    content.rejection_reason = reason
    db.commit()

    return {"status": "rejected", "content_id": content_id}


@router.post("/{content_id}/publish", response_model=PublishResult)
async def publish_content(
    content_id: int,
    request: PublishContentRequest = None,
    db: Session = Depends(get_db),
):
    """Publish approved content to Reddit."""
    content = db.query(GeneratedContent).get(content_id)

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    if content.status != ContentStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail="Content must be approved before publishing")

    if not content.opportunity_id:
        raise HTTPException(status_code=400, detail="Content has no associated opportunity")

    opportunity = db.query(Opportunity).get(content.opportunity_id)

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Publish
    publisher = RedditPublisher()
    result = publisher.publish_content(
        db=db,
        content=content,
        opportunity=opportunity,
        account_id=request.account_id if request else None,
    )

    return PublishResult(
        success=result.success,
        content_id=result.content_id,
        published_reddit_id=result.reddit_id,
        published_url=result.reddit_url,
        error=result.error,
    )


@router.get("/{content_id}/performance", response_model=ContentPerformanceResponse)
async def get_content_performance(
    content_id: int,
    db: Session = Depends(get_db),
):
    """Get performance history for published content."""
    content = db.query(GeneratedContent).get(content_id)

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    snapshots = db.query(ContentPerformance).filter(
        ContentPerformance.content_id == content_id
    ).order_by(ContentPerformance.snapshot_at.asc()).all()

    latest = snapshots[-1] if snapshots else None

    return ContentPerformanceResponse(
        content_id=content_id,
        current_score=latest.score if latest else 0,
        current_replies=latest.num_replies if latest else 0,
        is_removed=latest.is_removed if latest else False,
        snapshots=[PerformanceSnapshot.from_orm(s) for s in snapshots],
        total_snapshots=len(snapshots),
    )
