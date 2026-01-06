"""
Reddit Account management API endpoints.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import RedditAccount, AccountStatus
from app.schemas.reddit_account import (
    RedditAccountResponse,
    RedditAccountDetailResponse,
    RedditAccountListResponse,
    RedditAccountUpdate,
    AccountHealthCheck,
)
from app.services.reddit_publisher import RedditPublisher

router = APIRouter()


@router.get("/", response_model=RedditAccountListResponse)
async def list_accounts(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List Reddit accounts."""
    query = db.query(RedditAccount)

    if project_id:
        query = query.filter(RedditAccount.project_id == project_id)

    if status:
        query = query.filter(RedditAccount.status == status)

    accounts = query.order_by(RedditAccount.created_at.desc()).all()
    total = len(accounts)

    return RedditAccountListResponse(items=accounts, total=total)


@router.get("/{account_id}", response_model=RedditAccountDetailResponse)
async def get_account(
    account_id: int,
    db: Session = Depends(get_db),
):
    """Get account details."""
    account = db.query(RedditAccount).get(account_id)

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return RedditAccountDetailResponse(
        **account.__dict__,
        can_post=account.can_post,
        selection_score=account.selection_score,
    )


@router.put("/{account_id}", response_model=RedditAccountResponse)
async def update_account(
    account_id: int,
    account_in: RedditAccountUpdate,
    db: Session = Depends(get_db),
):
    """Update account settings."""
    account = db.query(RedditAccount).get(account_id)

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    update_data = account_in.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(account, field, value)

    db.commit()
    db.refresh(account)

    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
):
    """Remove a Reddit account."""
    account = db.query(RedditAccount).get(account_id)

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Don't actually delete - mark as inactive
    account.status = AccountStatus.INACTIVE.value
    db.commit()


@router.post("/{account_id}/health-check", response_model=AccountHealthCheck)
async def check_account_health(
    account_id: int,
    db: Session = Depends(get_db),
):
    """
    Trigger health check for an account.

    Verifies OAuth token and updates account metrics.
    """
    account = db.query(RedditAccount).get(account_id)

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    publisher = RedditPublisher()
    result = publisher.check_account_health(db, account)

    return AccountHealthCheck(
        account_id=result["account_id"],
        username=result["username"],
        status=result["status"],
        health_score=result["health_score"],
        karma_total=result["karma_total"],
        can_post=result["can_post"],
        issues=result["issues"],
    )


@router.post("/{account_id}/activate")
async def activate_account(
    account_id: int,
    db: Session = Depends(get_db),
):
    """Activate a deactivated account."""
    account = db.query(RedditAccount).get(account_id)

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.status == AccountStatus.SUSPENDED.value:
        raise HTTPException(status_code=400, detail="Cannot activate suspended account")

    # Run health check first
    publisher = RedditPublisher()
    result = publisher.check_account_health(db, account)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=f"Account has issues: {result['issues']}")

    return {"status": "activated", "account_id": account_id}


@router.post("/{account_id}/deactivate")
async def deactivate_account(
    account_id: int,
    db: Session = Depends(get_db),
):
    """Deactivate an account (stops using it for posting)."""
    account = db.query(RedditAccount).get(account_id)

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.status = AccountStatus.INACTIVE.value
    db.commit()

    # Clear cached client
    publisher = RedditPublisher()
    publisher.clear_client_cache(account_id)

    return {"status": "deactivated", "account_id": account_id}


@router.get("/{account_id}/activity")
async def get_account_activity(
    account_id: int,
    db: Session = Depends(get_db),
):
    """Get account activity summary by subreddit."""
    account = db.query(RedditAccount).get(account_id)

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    activity = account.subreddit_activity or {}

    # Format activity data
    formatted = []
    for subreddit, data in activity.items():
        formatted.append({
            "subreddit": subreddit,
            "posts": data.get("posts", 0),
            "karma": data.get("karma", 0),
            "last_activity": data.get("last_activity"),
        })

    # Sort by posts descending
    formatted.sort(key=lambda x: x["posts"], reverse=True)

    return {
        "account_id": account_id,
        "username": account.username,
        "total_posts": account.total_posts_made,
        "total_removed": account.total_posts_removed,
        "subreddit_activity": formatted,
    }
