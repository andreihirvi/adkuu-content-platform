"""
Dashboard API endpoints.
"""
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from pydantic import BaseModel

from app.api.deps import get_db
from app.models import (
    Project, Opportunity, GeneratedContent, ContentPerformance,
    RedditAccount, OpportunityStatus, ContentStatus, AccountStatus
)

router = APIRouter()


class OpportunityStats(BaseModel):
    total: int
    by_urgency: dict
    new_today: int


class ContentStats(BaseModel):
    pending_review: int
    published_today: int
    total_published: int


class PerformanceStats(BaseModel):
    total_upvotes: int
    avg_engagement_rate: float
    top_comments_count: int


class AccountStats(BaseModel):
    total: int
    healthy: int
    in_cooldown: int


class DashboardStats(BaseModel):
    opportunities: OpportunityStats
    content: ContentStats
    performance: PerformanceStats
    accounts: AccountStats


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get dashboard statistics."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Base filters
    opp_base_filter = []
    content_base_filter = []

    if project_id:
        opp_base_filter.append(Opportunity.project_id == project_id)
        content_base_filter.append(GeneratedContent.project_id == project_id)

    # Opportunity stats - using actual status values from the model
    total_opps = db.query(func.count(Opportunity.id)).filter(
        Opportunity.status.in_(['pending', 'approved', 'generating', 'ready']),
        *opp_base_filter
    ).scalar() or 0

    new_today = db.query(func.count(Opportunity.id)).filter(
        Opportunity.discovered_at >= today,
        *opp_base_filter
    ).scalar() or 0

    # Urgency breakdown - using 'urgency' field from model
    urgency_counts = db.query(
        Opportunity.urgency,
        func.count(Opportunity.id)
    ).filter(
        Opportunity.status.in_(['pending', 'approved', 'generating', 'ready']),
        *opp_base_filter
    ).group_by(Opportunity.urgency).all()

    by_urgency = {
        'critical': 0,  # Map 'urgent' to 'critical' for frontend
        'high': 0,
        'medium': 0,
        'low': 0,
    }
    for level, count in urgency_counts:
        if level == 'urgent':
            by_urgency['critical'] = count
        elif level in by_urgency:
            by_urgency[level] = count

    # Content stats - using actual status values from the model
    pending_review = db.query(func.count(GeneratedContent.id)).filter(
        GeneratedContent.status.in_(['draft', 'pending']),
        *content_base_filter
    ).scalar() or 0

    published_today = db.query(func.count(GeneratedContent.id)).filter(
        GeneratedContent.status == 'published',
        GeneratedContent.published_at >= today,
        *content_base_filter
    ).scalar() or 0

    total_published = db.query(func.count(GeneratedContent.id)).filter(
        GeneratedContent.status == 'published',
        *content_base_filter
    ).scalar() or 0

    # Performance stats
    perf_data = db.query(
        func.sum(ContentPerformance.score).label('total_upvotes'),
        func.avg(ContentPerformance.engagement_rate).label('avg_engagement'),
        func.count(ContentPerformance.id).filter(ContentPerformance.score >= 10).label('top_comments')
    ).join(
        GeneratedContent, ContentPerformance.content_id == GeneratedContent.id
    ).filter(
        GeneratedContent.status == 'published',
        *content_base_filter
    ).first()

    total_upvotes = int(perf_data.total_upvotes or 0) if perf_data else 0
    avg_engagement = float(perf_data.avg_engagement or 0) if perf_data else 0
    top_comments = int(perf_data.top_comments or 0) if perf_data else 0

    # Account stats
    total_accounts = db.query(func.count(RedditAccount.id)).scalar() or 0

    healthy_accounts = db.query(func.count(RedditAccount.id)).filter(
        RedditAccount.status == 'active',
        RedditAccount.health_score >= 0.8
    ).scalar() or 0

    in_cooldown = db.query(func.count(RedditAccount.id)).filter(
        RedditAccount.status.in_(['rate_limited', 'oauth_expired'])
    ).scalar() or 0

    return DashboardStats(
        opportunities=OpportunityStats(
            total=total_opps,
            by_urgency=by_urgency,
            new_today=new_today,
        ),
        content=ContentStats(
            pending_review=pending_review,
            published_today=published_today,
            total_published=total_published,
        ),
        performance=PerformanceStats(
            total_upvotes=total_upvotes,
            avg_engagement_rate=avg_engagement,
            top_comments_count=top_comments,
        ),
        accounts=AccountStats(
            total=total_accounts,
            healthy=healthy_accounts,
            in_cooldown=in_cooldown,
        ),
    )
