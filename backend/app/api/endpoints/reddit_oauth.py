"""
Reddit OAuth API endpoints.
"""
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import praw

from app.api.deps import get_db
from app.core.config import settings
from app.models import RedditAccount, Project
from app.schemas.reddit_account import OAuthInitResponse, OAuthCallbackResponse
from app.utils.encryption import encrypt_token

router = APIRouter()

# Store state tokens temporarily (in production, use Redis or database)
_oauth_states = {}


@router.get("/auth/url", response_model=OAuthInitResponse)
async def get_oauth_url(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Get Reddit OAuth authorization URL.

    Args:
        project_id: Optional project to associate the account with

    Returns:
        Authorization URL and state token
    """
    # Validate project if provided
    if project_id:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    # Generate state token
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "project_id": project_id,
        "created_at": None,  # Would add timestamp in production
    }

    # Create Reddit client for OAuth
    reddit = praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        redirect_uri=settings.REDDIT_REDIRECT_URI,
        user_agent=settings.REDDIT_USER_AGENT,
    )

    # Required scopes
    scopes = ["identity", "read", "submit", "vote", "history", "mysubreddits"]

    # Generate authorization URL
    auth_url = reddit.auth.url(
        scopes=scopes,
        state=state,
        duration="permanent"  # Get refresh token
    )

    return OAuthInitResponse(auth_url=auth_url, state=state)


@router.get("/auth/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Handle Reddit OAuth callback.

    Args:
        code: Authorization code from Reddit
        state: State token for verification
        error: Error message if authorization failed
    """
    # Check for errors
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    # Verify state
    if state not in _oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state token")

    state_data = _oauth_states.pop(state)
    project_id = state_data.get("project_id")

    try:
        # Create Reddit client
        reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            redirect_uri=settings.REDDIT_REDIRECT_URI,
            user_agent=settings.REDDIT_USER_AGENT,
        )

        # Exchange code for tokens
        refresh_token = reddit.auth.authorize(code)

        # Get user info
        user = reddit.user.me()

        # Check if account already exists
        existing = db.query(RedditAccount).filter(
            RedditAccount.username == user.name
        ).first()

        if existing:
            # Update existing account
            existing.refresh_token_encrypted = encrypt_token(refresh_token)
            existing.karma_total = user.total_karma
            existing.karma_comment = user.comment_karma
            existing.karma_post = user.link_karma
            existing.status = "active"
            existing.health_score = 1.0

            if project_id:
                existing.project_id = project_id

            db.commit()

            return OAuthCallbackResponse(
                success=True,
                account_id=existing.id,
                username=existing.username,
            )

        else:
            # Create new account
            from datetime import datetime

            account = RedditAccount(
                project_id=project_id,
                username=user.name,
                display_name=user.name,
                refresh_token_encrypted=encrypt_token(refresh_token),
                client_id=settings.REDDIT_CLIENT_ID,
                user_agent=settings.REDDIT_USER_AGENT,
                karma_total=user.total_karma,
                karma_comment=user.comment_karma,
                karma_post=user.link_karma,
                account_created_at=datetime.utcfromtimestamp(user.created_utc),
                account_age_days=(datetime.utcnow() - datetime.utcfromtimestamp(user.created_utc)).days,
                oauth_scopes=["identity", "read", "submit", "vote", "history", "mysubreddits"],
                status="active",
                health_score=1.0,
            )

            db.add(account)
            db.commit()
            db.refresh(account)

            return OAuthCallbackResponse(
                success=True,
                account_id=account.id,
                username=account.username,
            )

    except Exception as e:
        return OAuthCallbackResponse(
            success=False,
            error=f"OAuth failed: {str(e)}"
        )


@router.post("/auth/refresh/{account_id}")
async def refresh_token(
    account_id: int,
    db: Session = Depends(get_db),
):
    """
    Manually refresh OAuth token for an account.

    Args:
        account_id: Account ID to refresh
    """
    account = db.query(RedditAccount).get(account_id)

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if not account.refresh_token_encrypted:
        raise HTTPException(status_code=400, detail="Account has no refresh token")

    from app.services.reddit_publisher import RedditPublisher

    publisher = RedditPublisher()
    success = await publisher.refresh_account_token(db, account)

    if success:
        return {"status": "refreshed", "account_id": account_id}
    else:
        raise HTTPException(status_code=500, detail="Token refresh failed")
