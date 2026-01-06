"""
Project API endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, get_current_user_optional
from app.models import Project, ProjectStatus, Opportunity, GeneratedContent, RedditAccount, SubredditConfig
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    SubredditConfigCreate,
    SubredditConfigResponse,
)
from app.services.subreddit_analyzer import SubredditAnalyzer

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
):
    """Create a new project."""
    project = Project(
        name=project_in.name,
        description=project_in.description,
        brand_voice=project_in.brand_voice,
        product_context=project_in.product_context,
        website_url=project_in.website_url,
        target_subreddits=project_in.target_subreddits,
        keywords=project_in.keywords,
        negative_keywords=project_in.negative_keywords,
        automation_level=project_in.automation_level,
        status=ProjectStatus.ACTIVE.value,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    # Analyze target subreddits in background
    if project.target_subreddits:
        analyzer = SubredditAnalyzer()
        for subreddit_name in project.target_subreddits[:5]:  # Limit initial analysis
            try:
                analyzer.analyze_subreddit(db, subreddit_name, project.id)
            except Exception as e:
                pass  # Non-blocking

    return project


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all projects."""
    query = db.query(Project)

    if status:
        query = query.filter(Project.status == status)

    total = query.count()
    projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()

    return ProjectListResponse(
        items=projects,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    """Get project details."""
    project = db.query(Project).get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get statistics
    total_opps = db.query(func.count(Opportunity.id)).filter(
        Opportunity.project_id == project_id
    ).scalar()

    pending_opps = db.query(func.count(Opportunity.id)).filter(
        Opportunity.project_id == project_id,
        Opportunity.status == "pending"
    ).scalar()

    published_content = db.query(func.count(GeneratedContent.id)).filter(
        GeneratedContent.project_id == project_id,
        GeneratedContent.status == "published"
    ).scalar()

    connected_accounts = db.query(func.count(RedditAccount.id)).filter(
        RedditAccount.project_id == project_id,
        RedditAccount.status == "active"
    ).scalar()

    return ProjectDetailResponse(
        **project.__dict__,
        total_opportunities=total_opps,
        pending_opportunities=pending_opps,
        published_content=published_content,
        connected_accounts=connected_accounts,
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
):
    """Update a project."""
    project = db.query(Project).get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_in.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    """Delete (archive) a project."""
    project = db.query(Project).get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = ProjectStatus.ARCHIVED.value
    db.commit()


@router.post("/{project_id}/subreddits", response_model=SubredditConfigResponse)
async def add_subreddit(
    project_id: int,
    config_in: SubredditConfigCreate,
    db: Session = Depends(get_db),
):
    """Add a subreddit to project and analyze it."""
    project = db.query(Project).get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if already exists
    existing = db.query(SubredditConfig).filter(
        SubredditConfig.project_id == project_id,
        SubredditConfig.subreddit_name == config_in.subreddit_name
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Subreddit already configured")

    # Analyze and create config
    analyzer = SubredditAnalyzer()
    config = analyzer.analyze_subreddit(db, config_in.subreddit_name, project_id)

    # Apply any overrides from input
    if config_in.min_account_age_days is not None:
        config.min_account_age_days = config_in.min_account_age_days
    if config_in.min_karma is not None:
        config.min_karma = config_in.min_karma
    if config_in.posting_rules is not None:
        config.posting_rules = config_in.posting_rules
    config.is_enabled = config_in.is_enabled

    db.commit()
    db.refresh(config)

    # Add to project's target subreddits if not already there
    if config.subreddit_name not in project.target_subreddits:
        project.target_subreddits = project.target_subreddits + [config.subreddit_name]
        db.commit()

    return config


@router.get("/{project_id}/subreddits", response_model=List[SubredditConfigResponse])
async def list_subreddits(
    project_id: int,
    db: Session = Depends(get_db),
):
    """List configured subreddits for a project."""
    configs = db.query(SubredditConfig).filter(
        SubredditConfig.project_id == project_id
    ).all()

    return configs


@router.delete("/{project_id}/subreddits/{subreddit_name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_subreddit(
    project_id: int,
    subreddit_name: str,
    db: Session = Depends(get_db),
):
    """Remove a subreddit from project."""
    config = db.query(SubredditConfig).filter(
        SubredditConfig.project_id == project_id,
        SubredditConfig.subreddit_name == subreddit_name
    ).first()

    if config:
        db.delete(config)

    # Remove from target_subreddits
    project = db.query(Project).get(project_id)
    if project and subreddit_name in project.target_subreddits:
        project.target_subreddits = [s for s in project.target_subreddits if s != subreddit_name]

    db.commit()
