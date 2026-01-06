"""
Reddit API helper utilities for PRAW integration.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import praw
from praw.models import Submission, Comment, Subreddit

from app.core.config import settings
from app.utils.encryption import decrypt_token

logger = logging.getLogger(__name__)


class RedditClientFactory:
    """Factory for creating PRAW Reddit client instances."""

    @staticmethod
    def create_read_only_client() -> praw.Reddit:
        """
        Create a read-only Reddit client for mining.

        Returns:
            praw.Reddit: Read-only PRAW client
        """
        return praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
        )

    @staticmethod
    def create_authenticated_client(
        access_token: str,
        refresh_token: Optional[str] = None
    ) -> praw.Reddit:
        """
        Create an authenticated Reddit client for posting.

        Args:
            access_token: OAuth access token (encrypted)
            refresh_token: OAuth refresh token (encrypted)

        Returns:
            praw.Reddit: Authenticated PRAW client
        """
        # Decrypt tokens
        decrypted_access = decrypt_token(access_token)
        decrypted_refresh = decrypt_token(refresh_token) if refresh_token else None

        reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
            refresh_token=decrypted_refresh,
        )

        # Set the access token
        reddit.auth.authorize(decrypted_access)

        return reddit


def calculate_post_velocity(submission: Submission) -> float:
    """
    Calculate the velocity of a Reddit post.

    Velocity formula: (score/age_hours) * 0.7 + (comments/age_hours) * 0.3 * 10

    Args:
        submission: PRAW Submission object

    Returns:
        float: Velocity score
    """
    age_hours = get_post_age_hours(submission)

    if age_hours < 0.1:  # Less than 6 minutes old
        age_hours = 0.1  # Avoid division by very small numbers

    score_velocity = submission.score / age_hours
    comment_velocity = submission.num_comments / age_hours

    velocity = (score_velocity * 0.7) + (comment_velocity * 0.3 * 10)

    return velocity


def get_post_age_hours(submission: Submission) -> float:
    """
    Get the age of a post in hours.

    Args:
        submission: PRAW Submission object

    Returns:
        float: Age in hours
    """
    created_at = datetime.utcfromtimestamp(submission.created_utc)
    age_delta = datetime.utcnow() - created_at
    return age_delta.total_seconds() / 3600


def classify_urgency(velocity: float, age_hours: float, threshold: float) -> str:
    """
    Classify opportunity urgency based on velocity and age.

    Args:
        velocity: Post velocity score
        age_hours: Post age in hours
        threshold: Subreddit-specific velocity threshold

    Returns:
        str: Urgency level (urgent, high, medium, low, expired)
    """
    if age_hours > 6:
        return "expired"
    elif velocity > threshold * 2 and age_hours < 1:
        return "urgent"
    elif velocity > threshold and age_hours < 2:
        return "high"
    elif velocity > threshold * 0.5 and age_hours < 4:
        return "medium"
    else:
        return "low"


def get_velocity_threshold(subscribers: int) -> float:
    """
    Get velocity threshold based on subreddit size.

    Args:
        subscribers: Number of subreddit subscribers

    Returns:
        float: Velocity threshold
    """
    if subscribers < 50000:
        return 5.0
    elif subscribers < 500000:
        return 15.0
    elif subscribers < 2000000:
        return 50.0
    else:
        return 200.0


def extract_submission_data(submission: Submission) -> Dict[str, Any]:
    """
    Extract relevant data from a PRAW Submission object.

    Args:
        submission: PRAW Submission object

    Returns:
        Dict containing submission data
    """
    return {
        "reddit_post_id": submission.id,
        "subreddit": submission.subreddit.display_name,
        "post_title": submission.title,
        "post_content": submission.selftext if submission.is_self else None,
        "post_url": f"https://www.reddit.com{submission.permalink}",
        "post_author": str(submission.author) if submission.author else "[deleted]",
        "post_created_at": datetime.utcfromtimestamp(submission.created_utc),
        "post_score": submission.score,
        "post_num_comments": submission.num_comments,
        "post_upvote_ratio": submission.upvote_ratio,
        "is_self": submission.is_self,
        "link_flair_text": submission.link_flair_text,
        "over_18": submission.over_18,
    }


def extract_comment_metrics(comment: Comment) -> Dict[str, Any]:
    """
    Extract metrics from a PRAW Comment object.

    Args:
        comment: PRAW Comment object

    Returns:
        Dict containing comment metrics
    """
    return {
        "score": comment.score,
        "ups": getattr(comment, 'ups', comment.score),
        "downs": getattr(comment, 'downs', 0),
        "num_replies": len(comment.replies) if hasattr(comment, 'replies') else 0,
        "is_submitter": comment.is_submitter,
        "created_utc": datetime.utcfromtimestamp(comment.created_utc),
        "edited": bool(comment.edited),
        "controversiality": getattr(comment, 'controversiality', 0),
        "depth": getattr(comment, 'depth', 0),
    }


def check_comment_removed(reddit: praw.Reddit, comment_id: str) -> tuple[bool, Optional[str]]:
    """
    Check if a comment has been removed.

    Args:
        reddit: PRAW Reddit client
        comment_id: Reddit comment ID

    Returns:
        Tuple of (is_removed, removal_reason)
    """
    try:
        comment = reddit.comment(id=comment_id)
        comment._fetch()

        # Check if body is [removed] or [deleted]
        if comment.body in ["[removed]", "[deleted]"]:
            return True, "removed_by_moderator" if comment.body == "[removed]" else "deleted_by_author"

        # Check if author is None (deleted)
        if comment.author is None:
            return True, "author_deleted"

        return False, None

    except Exception as e:
        logger.error(f"Error checking comment {comment_id}: {e}")
        return False, None


def get_subreddit_info(reddit: praw.Reddit, subreddit_name: str) -> Dict[str, Any]:
    """
    Get information about a subreddit.

    Args:
        reddit: PRAW Reddit client
        subreddit_name: Name of the subreddit

    Returns:
        Dict containing subreddit info
    """
    try:
        subreddit = reddit.subreddit(subreddit_name)

        return {
            "name": subreddit.display_name,
            "subscribers": subreddit.subscribers,
            "active_users": subreddit.accounts_active,
            "public_description": subreddit.public_description,
            "subreddit_type": subreddit.subreddit_type,
            "over18": subreddit.over18,
            "created_utc": datetime.utcfromtimestamp(subreddit.created_utc),
        }
    except Exception as e:
        logger.error(f"Error getting subreddit info for {subreddit_name}: {e}")
        return {}


def get_rising_posts(
    reddit: praw.Reddit,
    subreddits: List[str],
    limit: int = 25
) -> List[Submission]:
    """
    Get rising posts from specified subreddits.

    Args:
        reddit: PRAW Reddit client
        subreddits: List of subreddit names
        limit: Maximum posts per subreddit

    Returns:
        List of Submission objects
    """
    posts = []

    for subreddit_name in subreddits:
        try:
            subreddit = reddit.subreddit(subreddit_name)

            # Get rising posts
            for submission in subreddit.rising(limit=limit):
                posts.append(submission)

            # Also get new posts (might be rising)
            for submission in subreddit.new(limit=limit):
                if submission not in posts:
                    posts.append(submission)

        except Exception as e:
            logger.error(f"Error getting posts from r/{subreddit_name}: {e}")
            continue

    return posts
