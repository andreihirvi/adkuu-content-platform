"""
Celery tasks for the Adkuu Content Platform.
"""
from app.tasks.mine_opportunities import (
    mine_opportunities_task,
    scheduled_mining_task,
    expire_opportunities_task,
    refresh_opportunity_scores_task,
)
from app.tasks.generate_content import (
    generate_content_task,
    regenerate_content_task,
    batch_generate_content_task,
    auto_generate_for_urgent_task,
)
from app.tasks.collect_analytics import (
    collect_content_analytics_task,
    collect_all_analytics_task,
    update_learning_features_task,
    calculate_project_metrics_task,
    detect_removals_task,
)
from app.tasks.check_account_health import (
    check_account_health_task,
    check_all_accounts_health_task,
    refresh_account_token_task,
    reset_daily_limits_task,
    recover_rate_limited_accounts_task,
    update_account_karma_task,
    detect_suspended_accounts_task,
)

__all__ = [
    # Mining tasks
    "mine_opportunities_task",
    "scheduled_mining_task",
    "expire_opportunities_task",
    "refresh_opportunity_scores_task",
    # Content generation tasks
    "generate_content_task",
    "regenerate_content_task",
    "batch_generate_content_task",
    "auto_generate_for_urgent_task",
    # Analytics tasks
    "collect_content_analytics_task",
    "collect_all_analytics_task",
    "update_learning_features_task",
    "calculate_project_metrics_task",
    "detect_removals_task",
    # Account health tasks
    "check_account_health_task",
    "check_all_accounts_health_task",
    "refresh_account_token_task",
    "reset_daily_limits_task",
    "recover_rate_limited_accounts_task",
    "update_account_karma_task",
    "detect_suspended_accounts_task",
]
