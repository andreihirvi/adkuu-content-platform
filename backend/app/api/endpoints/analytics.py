"""
Analytics API endpoints.
"""
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.api.deps import get_db
from app.models import (
    Project, Opportunity, GeneratedContent, ContentPerformance,
    RedditAccount, LearningFeature, SubredditConfig
)
from app.schemas.analytics import (
    ProjectAnalytics,
    TimeSeriesDataPoint,
    PerformanceTimeSeries,
    SubredditInsights,
    LearningFeatureResponse,
    DashboardSummary,
)
from app.services.reddit_analytics import RedditAnalyticsService

router = APIRouter()


@router.get("/projects/{project_id}/summary", response_model=ProjectAnalytics)
async def get_project_analytics(
    project_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get analytics summary for a project."""
    project = db.query(Project).get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Opportunity counts
    total_opps = db.query(func.count(Opportunity.id)).filter(
        Opportunity.project_id == project_id,
        Opportunity.discovered_at >= cutoff
    ).scalar()

    pending_opps = db.query(func.count(Opportunity.id)).filter(
        Opportunity.project_id == project_id,
        Opportunity.status == "pending"
    ).scalar()

    approved_opps = db.query(func.count(Opportunity.id)).filter(
        Opportunity.project_id == project_id,
        Opportunity.status == "approved",
        Opportunity.discovered_at >= cutoff
    ).scalar()

    published_opps = db.query(func.count(Opportunity.id)).filter(
        Opportunity.project_id == project_id,
        Opportunity.status == "published",
        Opportunity.discovered_at >= cutoff
    ).scalar()

    expired_opps = db.query(func.count(Opportunity.id)).filter(
        Opportunity.project_id == project_id,
        Opportunity.status == "expired",
        Opportunity.discovered_at >= cutoff
    ).scalar()

    # Content counts
    total_content = db.query(func.count(GeneratedContent.id)).filter(
        GeneratedContent.project_id == project_id,
        GeneratedContent.created_at >= cutoff
    ).scalar()

    approved_content = db.query(func.count(GeneratedContent.id)).filter(
        GeneratedContent.project_id == project_id,
        GeneratedContent.status == "approved",
        GeneratedContent.created_at >= cutoff
    ).scalar()

    published_content = db.query(func.count(GeneratedContent.id)).filter(
        GeneratedContent.project_id == project_id,
        GeneratedContent.status == "published",
        GeneratedContent.created_at >= cutoff
    ).scalar()

    rejected_content = db.query(func.count(GeneratedContent.id)).filter(
        GeneratedContent.project_id == project_id,
        GeneratedContent.status == "rejected",
        GeneratedContent.created_at >= cutoff
    ).scalar()

    # Performance metrics from analytics service
    analytics_service = RedditAnalyticsService()
    metrics = analytics_service.calculate_project_metrics(db, project_id, days)

    # Get top subreddits
    top_subreddits = db.query(
        Opportunity.subreddit,
        func.count(Opportunity.id).label("count")
    ).filter(
        Opportunity.project_id == project_id,
        Opportunity.status == "published"
    ).group_by(Opportunity.subreddit).order_by(desc("count")).limit(5).all()

    # Get best posting hours from learning features
    timing_features = db.query(LearningFeature).filter(
        LearningFeature.project_id == project_id,
        LearningFeature.feature_type == "timing"
    ).order_by(desc(LearningFeature.success_rate)).limit(5).all()

    best_hours = [int(f.feature_key) for f in timing_features if f.feature_key.isdigit()]

    return ProjectAnalytics(
        project_id=project_id,
        project_name=project.name,
        period_days=days,
        total_opportunities=total_opps,
        pending_opportunities=pending_opps,
        approved_opportunities=approved_opps,
        published_opportunities=published_opps,
        expired_opportunities=expired_opps,
        total_content_generated=total_content,
        content_approved=approved_content,
        content_published=published_content,
        content_rejected=rejected_content,
        avg_content_score=metrics.get("avg_score"),
        total_engagement=metrics.get("total_score", 0) + metrics.get("total_replies", 0),
        removal_rate=metrics.get("removal_rate", 0),
        top_subreddits=[{"subreddit": s[0], "count": s[1]} for s in top_subreddits],
        best_posting_hours=best_hours,
    )


@router.get("/projects/{project_id}/performance", response_model=PerformanceTimeSeries)
async def get_performance_timeseries(
    project_id: int,
    metric: str = Query("score", enum=["score", "engagement", "published"]),
    granularity: str = Query("day", enum=["hour", "day", "week"]),
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Get performance time series data."""
    project = db.query(Project).get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get published content
    contents = db.query(GeneratedContent).filter(
        GeneratedContent.project_id == project_id,
        GeneratedContent.status == "published",
        GeneratedContent.published_at >= cutoff
    ).all()

    # Build time series based on metric
    data_points = []

    if metric == "published":
        # Count publications per time bucket
        for content in contents:
            if content.published_at:
                data_points.append(TimeSeriesDataPoint(
                    timestamp=content.published_at,
                    value=1,
                ))
    else:
        # Use performance snapshots
        for content in contents:
            latest_perf = db.query(ContentPerformance).filter(
                ContentPerformance.content_id == content.id
            ).order_by(desc(ContentPerformance.snapshot_at)).first()

            if latest_perf:
                value = latest_perf.score if metric == "score" else (latest_perf.score + latest_perf.num_replies)
                data_points.append(TimeSeriesDataPoint(
                    timestamp=latest_perf.snapshot_at,
                    value=value,
                ))

    return PerformanceTimeSeries(
        project_id=project_id,
        metric=metric,
        granularity=granularity,
        data=sorted(data_points, key=lambda x: x.timestamp),
        total_points=len(data_points),
    )


@router.get("/subreddits/{subreddit_name}/insights", response_model=SubredditInsights)
async def get_subreddit_insights(
    subreddit_name: str,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get insights for a specific subreddit."""
    # Get subreddit config
    query = db.query(SubredditConfig).filter(
        SubredditConfig.subreddit_name == subreddit_name
    )

    if project_id:
        query = query.filter(SubredditConfig.project_id == project_id)

    config = query.first()

    # Get performance data
    analytics_service = RedditAnalyticsService()

    if project_id:
        perf = analytics_service.get_subreddit_performance(db, project_id, subreddit_name)
    else:
        perf = {"total_posts": 0, "avg_score": 0, "removal_rate": 0}

    # Build recommendations
    recommendations = []

    if config:
        if config.velocity_threshold:
            recommendations.append(f"Target posts with velocity > {config.velocity_threshold:.0f}")

        if config.best_posting_hours:
            hours_str = ", ".join(f"{h}:00" for h in config.best_posting_hours[:3])
            recommendations.append(f"Best posting times (UTC): {hours_str}")

        if config.min_karma:
            recommendations.append(f"Account needs at least {config.min_karma} karma")

    return SubredditInsights(
        subreddit_name=subreddit_name,
        subscribers=config.subscribers if config else None,
        total_posts=perf.get("total_posts", 0),
        successful_posts=perf.get("total_posts", 0) - perf.get("removal_count", 0),
        avg_score=perf.get("avg_score"),
        removal_rate=perf.get("removal_rate", 0),
        best_hours=config.best_posting_hours if config else [],
        best_days=config.best_posting_days if config else [],
        velocity_threshold=config.velocity_threshold if config else 15.0,
        recommendations=recommendations,
    )


@router.get("/learning-features", response_model=List[LearningFeatureResponse])
async def get_learning_features(
    project_id: Optional[int] = None,
    feature_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get learned features."""
    query = db.query(LearningFeature)

    if project_id:
        query = query.filter(LearningFeature.project_id == project_id)

    if feature_type:
        query = query.filter(LearningFeature.feature_type == feature_type)

    features = query.order_by(desc(LearningFeature.success_rate)).limit(limit).all()

    return [LearningFeatureResponse.from_orm(f) for f in features]


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get dashboard summary."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Base filters
    opp_filter = [Opportunity.discovered_at >= today]
    content_filter = [GeneratedContent.published_at >= today]
    account_filter = []

    if project_id:
        opp_filter.append(Opportunity.project_id == project_id)
        content_filter.append(GeneratedContent.project_id == project_id)
        account_filter.append(RedditAccount.project_id == project_id)

    # Today's stats
    opps_today = db.query(func.count(Opportunity.id)).filter(*opp_filter).scalar()
    published_today = db.query(func.count(GeneratedContent.id)).filter(
        GeneratedContent.status == "published",
        *content_filter
    ).scalar()

    # Pending actions
    pending_review = db.query(func.count(GeneratedContent.id)).filter(
        GeneratedContent.status.in_(["draft", "pending"])
    ).scalar()

    urgent_opps = db.query(func.count(Opportunity.id)).filter(
        Opportunity.status == "pending",
        Opportunity.urgency == "urgent"
    ).scalar()

    # Account health
    active_accounts = db.query(func.count(RedditAccount.id)).filter(
        RedditAccount.status == "active",
        *account_filter
    ).scalar()

    accounts_with_issues = db.query(func.count(RedditAccount.id)).filter(
        RedditAccount.status.in_(["rate_limited", "oauth_expired"]),
        *account_filter
    ).scalar()

    # Recent publications
    recent_pubs = db.query(GeneratedContent).filter(
        GeneratedContent.status == "published"
    ).order_by(desc(GeneratedContent.published_at)).limit(5).all()

    recent_publications = [
        {
            "content_id": c.id,
            "published_at": c.published_at.isoformat() if c.published_at else None,
            "subreddit": None,  # Would need to join with opportunity
        }
        for c in recent_pubs
    ]

    return DashboardSummary(
        opportunities_today=opps_today,
        content_published_today=published_today,
        engagement_today=0,  # Would calculate from performance
        pending_review=pending_review,
        urgent_opportunities=urgent_opps,
        active_accounts=active_accounts,
        accounts_with_issues=accounts_with_issues,
        recent_publications=recent_publications,
        recent_high_performers=[],
    )
