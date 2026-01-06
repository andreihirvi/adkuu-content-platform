"""
Reddit Publisher Service - handles multi-account publishing to Reddit.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import praw
from praw.exceptions import RedditAPIException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import RedditAccount, AccountStatus, GeneratedContent, ContentStatus, Opportunity
from app.utils.encryption import decrypt_token, encrypt_token
from app.utils.text_processing import sanitize_for_reddit

logger = logging.getLogger(__name__)


class PublishResult:
    """Result of a publish operation."""

    def __init__(
        self,
        success: bool,
        content_id: int,
        reddit_id: Optional[str] = None,
        reddit_url: Optional[str] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.content_id = content_id
        self.reddit_id = reddit_id
        self.reddit_url = reddit_url
        self.error = error


class RedditPublisher:
    """
    Service for publishing content to Reddit.

    Supports multi-account management with:
    - Account selection based on health and subreddit fit
    - Rate limiting per account
    - OAuth token refresh
    - Error handling and recovery
    """

    def __init__(self):
        self._clients: Dict[int, praw.Reddit] = {}

    def publish_content(
        self,
        db: Session,
        content: GeneratedContent,
        opportunity: Opportunity,
        account_id: Optional[int] = None
    ) -> PublishResult:
        """
        Publish content to Reddit.

        Args:
            db: Database session
            content: Content to publish
            opportunity: Associated opportunity
            account_id: Optional specific account to use

        Returns:
            PublishResult with success status and details
        """
        # Select account
        if account_id:
            account = db.query(RedditAccount).get(account_id)
            if not account or not account.can_post:
                return PublishResult(
                    success=False,
                    content_id=content.id,
                    error=f"Account {account_id} not available for posting"
                )
        else:
            account = self._select_best_account(db, content.project_id, opportunity.subreddit)
            if not account:
                return PublishResult(
                    success=False,
                    content_id=content.id,
                    error="No available accounts for posting"
                )

        try:
            # Get authenticated Reddit client
            reddit = self._get_client(account)

            # Sanitize content
            text = sanitize_for_reddit(content.content_text)

            # Post comment
            submission = reddit.submission(id=opportunity.reddit_post_id)
            comment = submission.reply(text)

            # Update content record
            content.reddit_account_id = account.id
            content.published_reddit_id = comment.id
            content.published_url = f"https://www.reddit.com{comment.permalink}"
            content.published_at = datetime.utcnow()
            content.status = ContentStatus.PUBLISHED.value

            # Update account usage
            account.last_action_at = datetime.utcnow()
            account.daily_actions_count += 1
            account.total_posts_made += 1
            account.consecutive_failures = 0

            # Update subreddit activity
            subreddit_activity = account.subreddit_activity or {}
            if opportunity.subreddit not in subreddit_activity:
                subreddit_activity[opportunity.subreddit] = {
                    "posts": 0,
                    "karma": 0,
                    "last_activity": None
                }
            subreddit_activity[opportunity.subreddit]["posts"] += 1
            subreddit_activity[opportunity.subreddit]["last_activity"] = datetime.utcnow().isoformat()
            account.subreddit_activity = subreddit_activity

            # Update opportunity
            opportunity.status = "published"
            opportunity.processed_at = datetime.utcnow()

            db.commit()

            logger.info(f"Published content {content.id} to r/{opportunity.subreddit} via account {account.username}")

            return PublishResult(
                success=True,
                content_id=content.id,
                reddit_id=comment.id,
                reddit_url=content.published_url
            )

        except RedditAPIException as e:
            return self._handle_reddit_error(db, account, content, e)

        except Exception as e:
            logger.error(f"Error publishing content {content.id}: {e}")

            # Update failure count
            account.consecutive_failures += 1
            if account.consecutive_failures >= 3:
                account.health_score = max(0, account.health_score - 0.2)
            db.commit()

            return PublishResult(
                success=False,
                content_id=content.id,
                error=str(e)
            )

    def _get_client(self, account: RedditAccount) -> praw.Reddit:
        """Get or create authenticated Reddit client for account."""
        if account.id in self._clients:
            return self._clients[account.id]

        # Decrypt tokens
        refresh_token = decrypt_token(account.refresh_token_encrypted) if account.refresh_token_encrypted else None

        # Create client
        reddit = praw.Reddit(
            client_id=account.client_id or settings.REDDIT_CLIENT_ID,
            client_secret=decrypt_token(account.client_secret_encrypted) if account.client_secret_encrypted else settings.REDDIT_CLIENT_SECRET,
            user_agent=account.user_agent or settings.REDDIT_USER_AGENT,
            refresh_token=refresh_token,
        )

        self._clients[account.id] = reddit
        return reddit

    def _select_best_account(
        self,
        db: Session,
        project_id: int,
        subreddit: str
    ) -> Optional[RedditAccount]:
        """
        Select the best account for posting to a subreddit.

        Selection criteria:
        1. Must be active and can_post
        2. Prefer accounts with history in the subreddit
        3. Prefer accounts with higher karma
        4. Prefer accounts with lower removal rate
        """
        # Get all active accounts for project
        accounts = db.query(RedditAccount).filter(
            RedditAccount.project_id == project_id,
            RedditAccount.status == AccountStatus.ACTIVE.value
        ).all()

        if not accounts:
            return None

        # Filter to accounts that can post
        available = [a for a in accounts if a.can_post]

        if not available:
            return None

        # Score each account
        scored = []
        for account in available:
            score = account.selection_score

            # Bonus for subreddit history
            activity = account.subreddit_activity or {}
            if subreddit in activity:
                score += 15
                # Additional bonus for positive karma in subreddit
                if activity[subreddit].get("karma", 0) > 0:
                    score += 10

            scored.append((account, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[0][0] if scored else None

    def _handle_reddit_error(
        self,
        db: Session,
        account: RedditAccount,
        content: GeneratedContent,
        error: RedditAPIException
    ) -> PublishResult:
        """Handle Reddit API errors."""
        error_type = error.error_type if hasattr(error, 'error_type') else str(error)

        logger.error(f"Reddit API error for account {account.username}: {error_type}")

        # Update account status based on error
        if "RATELIMIT" in str(error).upper():
            account.status = AccountStatus.RATE_LIMITED.value
            account.health_score = 0.5

        elif "SUSPENDED" in str(error).upper() or "BANNED" in str(error).upper():
            account.status = AccountStatus.SUSPENDED.value
            account.health_score = 0.0

        elif "TOKEN" in str(error).upper() or "AUTH" in str(error).upper():
            account.status = AccountStatus.OAUTH_EXPIRED.value
            account.health_score = 0.3

        account.consecutive_failures += 1
        content.status = ContentStatus.FAILED.value
        db.commit()

        return PublishResult(
            success=False,
            content_id=content.id,
            error=f"Reddit API error: {error_type}"
        )

    async def refresh_account_token(
        self,
        db: Session,
        account: RedditAccount
    ) -> bool:
        """
        Refresh OAuth token for an account.

        Args:
            db: Database session
            account: Account to refresh

        Returns:
            bool: Success status
        """
        if not account.refresh_token_encrypted:
            logger.warning(f"Account {account.username} has no refresh token")
            return False

        try:
            # Get client (will use refresh token automatically)
            reddit = self._get_client(account)

            # Verify authentication
            user = reddit.user.me()

            # Update account info
            account.karma_total = user.total_karma
            account.karma_comment = user.comment_karma
            account.karma_post = user.link_karma
            account.status = AccountStatus.ACTIVE.value
            account.health_score = 1.0
            account.last_health_check_at = datetime.utcnow()

            db.commit()

            logger.info(f"Refreshed token for account {account.username}")
            return True

        except Exception as e:
            logger.error(f"Failed to refresh token for {account.username}: {e}")
            account.status = AccountStatus.OAUTH_EXPIRED.value
            account.health_score = 0.3
            db.commit()
            return False

    def check_account_health(
        self,
        db: Session,
        account: RedditAccount
    ) -> Dict[str, Any]:
        """
        Check health status of an account.

        Args:
            db: Database session
            account: Account to check

        Returns:
            Dict with health status details
        """
        issues = []
        status = "healthy"

        try:
            reddit = self._get_client(account)
            user = reddit.user.me()

            # Update metrics
            account.karma_total = user.total_karma
            account.karma_comment = user.comment_karma
            account.karma_post = user.link_karma

            # Check karma threshold
            if account.karma_comment < 100:
                issues.append("Low comment karma")
                status = "warning"

            # Check account age
            if account.account_age_days and account.account_age_days < 30:
                issues.append("Account too new")
                status = "warning"

            # Check removal rate
            if account.removal_rate > 0.2:
                issues.append("High removal rate")
                status = "warning"

            # Reset daily actions if needed
            if account.daily_actions_reset_at:
                if datetime.utcnow() - account.daily_actions_reset_at > timedelta(days=1):
                    account.daily_actions_count = 0
                    account.daily_actions_reset_at = datetime.utcnow()

            account.status = AccountStatus.ACTIVE.value
            account.health_score = 1.0 if not issues else 0.7
            account.last_health_check_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Health check failed for {account.username}: {e}")
            issues.append(f"Authentication failed: {str(e)}")
            status = "error"
            account.status = AccountStatus.OAUTH_EXPIRED.value
            account.health_score = 0.3

        db.commit()

        return {
            "account_id": account.id,
            "username": account.username,
            "status": status,
            "health_score": account.health_score,
            "karma_total": account.karma_total,
            "can_post": account.can_post,
            "issues": issues,
        }

    def clear_client_cache(self, account_id: int = None):
        """Clear cached Reddit clients."""
        if account_id:
            self._clients.pop(account_id, None)
        else:
            self._clients.clear()
