"""
Celery tasks for Reddit account health monitoring.
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from celery import shared_task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.db.database import SessionLocal
from app.models import RedditAccount, AccountStatus
from app.services.reddit_publisher import RedditPublisher

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.check_account_health",
    max_retries=2,
    default_retry_delay=60,
    queue="account-health",
)
def check_account_health_task(self, account_id: int):
    """
    Check health of a single Reddit account.

    Verifies OAuth token and updates account metrics.

    Args:
        account_id: Account ID to check
    """
    db = SessionLocal()

    try:
        account = db.query(RedditAccount).get(account_id)

        if not account:
            logger.error(f"Account {account_id} not found")
            return {"error": "Account not found"}

        logger.info(f"Checking health for account {account_id} ({account.username})")

        publisher = RedditPublisher()
        result = publisher.check_account_health(db, account)

        logger.info(
            f"Health check for account {account_id}: "
            f"status={result['status']}, health={result['health_score']:.2f}"
        )

        return result

    except Exception as e:
        logger.exception(f"Health check failed for account {account_id}: {e}")
        self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(
    name="tasks.check_all_accounts_health",
    queue="account-health",
)
def check_all_accounts_health_task():
    """
    Check health for all active accounts.

    Runs periodically to detect issues early.
    """
    db = SessionLocal()

    try:
        # Get accounts that haven't been checked recently
        check_cutoff = datetime.utcnow() - timedelta(hours=1)

        accounts = db.query(RedditAccount).filter(
            RedditAccount.status.in_([
                AccountStatus.ACTIVE.value,
                AccountStatus.RATE_LIMITED.value,
                AccountStatus.OAUTH_EXPIRED.value
            ])
        ).filter(
            (RedditAccount.last_health_check_at.is_(None)) |
            (RedditAccount.last_health_check_at < check_cutoff)
        ).all()

        logger.info(f"Checking health for {len(accounts)} accounts")

        queued = 0

        for account in accounts:
            try:
                check_account_health_task.delay(account.id)
                queued += 1
            except Exception as e:
                logger.error(f"Failed to queue health check for account {account.id}: {e}")

        return {"queued_count": queued}

    except Exception as e:
        logger.exception(f"Check all accounts health task failed: {e}")
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="tasks.refresh_account_token",
    max_retries=3,
    default_retry_delay=30,
    queue="account-health",
)
def refresh_account_token_task(self, account_id: int):
    """
    Refresh OAuth token for an account.

    Args:
        account_id: Account ID to refresh token for
    """
    db = SessionLocal()

    try:
        account = db.query(RedditAccount).get(account_id)

        if not account:
            logger.error(f"Account {account_id} not found")
            return {"error": "Account not found"}

        if not account.refresh_token_encrypted:
            logger.error(f"Account {account_id} has no refresh token")
            return {"error": "No refresh token"}

        logger.info(f"Refreshing token for account {account_id} ({account.username})")

        publisher = RedditPublisher()

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            success = loop.run_until_complete(
                publisher.refresh_account_token(db, account)
            )
        finally:
            loop.close()

        if success:
            logger.info(f"Token refreshed for account {account_id}")
            return {"success": True, "account_id": account_id}
        else:
            logger.warning(f"Token refresh failed for account {account_id}")
            return {"success": False, "account_id": account_id}

    except Exception as e:
        logger.exception(f"Token refresh failed for account {account_id}: {e}")
        self.retry(exc=e)

    finally:
        db.close()


@celery_app.task(
    name="tasks.reset_daily_limits",
    queue="account-health",
)
def reset_daily_limits_task():
    """
    Reset daily action counters for all accounts.

    Should run at midnight UTC.
    """
    db = SessionLocal()

    try:
        now = datetime.utcnow()

        # Get accounts that need reset
        accounts = db.query(RedditAccount).filter(
            (RedditAccount.daily_actions_reset_at.is_(None)) |
            (RedditAccount.daily_actions_reset_at < now.replace(hour=0, minute=0, second=0))
        ).all()

        reset_count = 0

        for account in accounts:
            account.daily_actions_count = 0
            account.daily_actions_reset_at = now
            reset_count += 1

        db.commit()

        logger.info(f"Reset daily limits for {reset_count} accounts")

        return {"reset_count": reset_count}

    except Exception as e:
        logger.exception(f"Reset daily limits task failed: {e}")
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(
    name="tasks.recover_rate_limited_accounts",
    queue="account-health",
)
def recover_rate_limited_accounts_task():
    """
    Attempt to recover rate-limited accounts.

    Checks if cooldown period has passed and re-activates accounts.
    """
    db = SessionLocal()

    try:
        # Rate limit typically lasts 10 minutes
        cooldown_cutoff = datetime.utcnow() - timedelta(minutes=15)

        rate_limited = db.query(RedditAccount).filter(
            RedditAccount.status == AccountStatus.RATE_LIMITED.value,
            RedditAccount.last_action_at < cooldown_cutoff
        ).all()

        recovered = 0

        for account in rate_limited:
            # Try a health check to verify account is working
            try:
                publisher = RedditPublisher()
                result = publisher.check_account_health(db, account)

                if result.get("status") != "error":
                    account.status = AccountStatus.ACTIVE.value
                    recovered += 1
                    logger.info(f"Recovered rate-limited account {account.id} ({account.username})")

            except Exception as e:
                logger.warning(f"Could not recover account {account.id}: {e}")

        db.commit()

        logger.info(f"Recovered {recovered} rate-limited accounts")

        return {"recovered_count": recovered}

    except Exception as e:
        logger.exception(f"Recover rate limited accounts task failed: {e}")
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(
    name="tasks.update_account_karma",
    queue="account-health",
)
def update_account_karma_task(account_id: Optional[int] = None):
    """
    Update karma statistics for accounts.

    Args:
        account_id: Specific account to update (all active if None)
    """
    db = SessionLocal()

    try:
        query = db.query(RedditAccount).filter(
            RedditAccount.status == AccountStatus.ACTIVE.value
        )

        if account_id:
            query = query.filter(RedditAccount.id == account_id)

        accounts = query.all()

        logger.info(f"Updating karma for {len(accounts)} accounts")

        publisher = RedditPublisher()
        updated = 0

        for account in accounts:
            try:
                # Get Reddit client for account
                client = publisher._get_reddit_client(db, account)

                if client:
                    user = client.user.me()

                    account.karma_total = user.total_karma
                    account.karma_comment = user.comment_karma
                    account.karma_post = user.link_karma
                    updated += 1

            except Exception as e:
                logger.warning(f"Could not update karma for account {account.id}: {e}")

        db.commit()

        logger.info(f"Updated karma for {updated} accounts")

        return {"updated_count": updated}

    except Exception as e:
        logger.exception(f"Update account karma task failed: {e}")
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()


@celery_app.task(
    name="tasks.detect_suspended_accounts",
    queue="account-health",
)
def detect_suspended_accounts_task():
    """
    Detect accounts that have been suspended by Reddit.

    Marks accounts appropriately so they're not used for posting.
    """
    db = SessionLocal()

    try:
        active_accounts = db.query(RedditAccount).filter(
            RedditAccount.status == AccountStatus.ACTIVE.value
        ).all()

        suspended_count = 0
        publisher = RedditPublisher()

        for account in active_accounts:
            try:
                client = publisher._get_reddit_client(db, account)

                if client:
                    # Try to access user info - will fail if suspended
                    try:
                        user = client.user.me()

                        # Check if user is suspended
                        if hasattr(user, 'is_suspended') and user.is_suspended:
                            account.status = AccountStatus.SUSPENDED.value
                            account.health_score = 0.0
                            suspended_count += 1
                            logger.warning(f"Account {account.id} ({account.username}) is suspended")

                    except Exception as user_error:
                        # If we can't access user, might be suspended
                        if "suspended" in str(user_error).lower():
                            account.status = AccountStatus.SUSPENDED.value
                            account.health_score = 0.0
                            suspended_count += 1
                            logger.warning(f"Account {account.id} ({account.username}) appears suspended")

            except Exception as e:
                logger.warning(f"Could not check account {account.id}: {e}")

        db.commit()

        logger.info(f"Detected {suspended_count} suspended accounts")

        return {"suspended_count": suspended_count}

    except Exception as e:
        logger.exception(f"Detect suspended accounts task failed: {e}")
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()
