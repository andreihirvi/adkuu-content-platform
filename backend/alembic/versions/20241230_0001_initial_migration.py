"""Initial migration - create all tables

Revision ID: 0001
Revises:
Create Date: 2024-12-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('brand_voice', sa.Text(), nullable=True),
        sa.Column('target_subreddits', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('product_context', sa.Text(), nullable=True),
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.Column('automation_level', sa.Integer(), nullable=True, default=1),
        sa.Column('status', sa.String(length=50), nullable=True, default='active'),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_name'), 'projects', ['name'], unique=False)

    # Create opportunities table
    op.create_table(
        'opportunities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('reddit_post_id', sa.String(length=50), nullable=False),
        sa.Column('subreddit', sa.String(length=100), nullable=False),
        sa.Column('post_title', sa.Text(), nullable=False),
        sa.Column('post_content', sa.Text(), nullable=True),
        sa.Column('post_url', sa.String(length=500), nullable=False),
        sa.Column('post_author', sa.String(length=100), nullable=True),
        sa.Column('post_created_at', sa.DateTime(), nullable=True),
        sa.Column('post_score', sa.Integer(), nullable=True, default=0),
        sa.Column('post_num_comments', sa.Integer(), nullable=True, default=0),
        sa.Column('post_upvote_ratio', sa.Float(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('virality_score', sa.Float(), nullable=True),
        sa.Column('timing_score', sa.Float(), nullable=True),
        sa.Column('composite_score', sa.Float(), nullable=True),
        sa.Column('urgency', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, default='pending'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('opportunity_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reddit_post_id')
    )
    op.create_index(op.f('ix_opportunities_id'), 'opportunities', ['id'], unique=False)
    op.create_index('idx_opp_project_status', 'opportunities', ['project_id', 'status'], unique=False)
    op.create_index('idx_opp_composite', 'opportunities', ['composite_score'], unique=False)

    # Create reddit_accounts table
    op.create_table(
        'reddit_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('access_token_encrypted', sa.Text(), nullable=True),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('client_id', sa.String(length=100), nullable=True),
        sa.Column('client_secret_encrypted', sa.Text(), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('oauth_scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('karma_total', sa.Integer(), nullable=True, default=0),
        sa.Column('karma_comment', sa.Integer(), nullable=True, default=0),
        sa.Column('karma_post', sa.Integer(), nullable=True, default=0),
        sa.Column('account_created_at', sa.DateTime(), nullable=True),
        sa.Column('account_age_days', sa.Integer(), nullable=True),
        sa.Column('last_action_at', sa.DateTime(), nullable=True),
        sa.Column('daily_actions_count', sa.Integer(), nullable=True, default=0),
        sa.Column('daily_actions_reset_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, default='active'),
        sa.Column('health_score', sa.Float(), nullable=True, default=1.0),
        sa.Column('last_health_check_at', sa.DateTime(), nullable=True),
        sa.Column('total_posts_made', sa.Integer(), nullable=True, default=0),
        sa.Column('total_posts_removed', sa.Integer(), nullable=True, default=0),
        sa.Column('subreddit_activity', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('account_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reddit_accounts_id'), 'reddit_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_reddit_accounts_username'), 'reddit_accounts', ['username'], unique=True)

    # Create generated_content table
    op.create_table(
        'generated_content',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('opportunity_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('content_text', sa.Text(), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=True, default='comment'),
        sa.Column('style', sa.String(length=50), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('quality_checks', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('passed_quality_gates', sa.Boolean(), nullable=True, default=False),
        sa.Column('status', sa.String(length=50), nullable=True, default='draft'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('reddit_account_id', sa.Integer(), nullable=True),
        sa.Column('published_reddit_id', sa.String(length=50), nullable=True),
        sa.Column('published_url', sa.String(length=500), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True, default=1),
        sa.Column('parent_content_id', sa.Integer(), nullable=True),
        sa.Column('content_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_content_id'], ['generated_content.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reddit_account_id'], ['reddit_accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_generated_content_id'), 'generated_content', ['id'], unique=False)
    op.create_index('idx_content_project_status', 'generated_content', ['project_id', 'status'], unique=False)

    # Create content_performance table
    op.create_table(
        'content_performance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_at', sa.DateTime(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True, default=0),
        sa.Column('upvotes', sa.Integer(), nullable=True, default=0),
        sa.Column('downvotes', sa.Integer(), nullable=True, default=0),
        sa.Column('num_replies', sa.Integer(), nullable=True, default=0),
        sa.Column('engagement_rate', sa.Float(), nullable=True),
        sa.Column('velocity', sa.Float(), nullable=True),
        sa.Column('is_removed', sa.Boolean(), nullable=True, default=False),
        sa.Column('removal_reason', sa.String(length=255), nullable=True),
        sa.Column('platform_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['content_id'], ['generated_content.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_content_performance_id'), 'content_performance', ['id'], unique=False)
    op.create_index('idx_perf_content', 'content_performance', ['content_id'], unique=False)

    # Create subreddit_configs table
    op.create_table(
        'subreddit_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('subreddit_name', sa.String(length=100), nullable=False),
        sa.Column('subscribers', sa.Integer(), nullable=True),
        sa.Column('active_users', sa.Integer(), nullable=True),
        sa.Column('min_account_age_days', sa.Integer(), nullable=True),
        sa.Column('min_karma', sa.Integer(), nullable=True),
        sa.Column('posting_rules', sa.Text(), nullable=True),
        sa.Column('allowed_content_types', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('flair_required', sa.Boolean(), nullable=True, default=False),
        sa.Column('available_flairs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('best_posting_hours', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('best_posting_days', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('avg_post_score', sa.Float(), nullable=True),
        sa.Column('avg_comment_score', sa.Float(), nullable=True),
        sa.Column('velocity_threshold', sa.Float(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('priority', sa.Integer(), nullable=True, default=1),
        sa.Column('last_analyzed_at', sa.DateTime(), nullable=True),
        sa.Column('analysis_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'subreddit_name', name='uix_project_subreddit')
    )
    op.create_index(op.f('ix_subreddit_configs_id'), 'subreddit_configs', ['id'], unique=False)

    # Create learning_features table
    op.create_table(
        'learning_features',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('feature_type', sa.String(length=50), nullable=False),
        sa.Column('feature_key', sa.String(length=255), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=True, default=0),
        sa.Column('success_count', sa.Integer(), nullable=True, default=0),
        sa.Column('failure_count', sa.Integer(), nullable=True, default=0),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('avg_score', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('feature_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('feature_type', 'feature_key', 'project_id', name='uix_feature_project')
    )
    op.create_index(op.f('ix_learning_features_id'), 'learning_features', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_learning_features_id'), table_name='learning_features')
    op.drop_table('learning_features')

    op.drop_index(op.f('ix_subreddit_configs_id'), table_name='subreddit_configs')
    op.drop_table('subreddit_configs')

    op.drop_index('idx_perf_content', table_name='content_performance')
    op.drop_index(op.f('ix_content_performance_id'), table_name='content_performance')
    op.drop_table('content_performance')

    op.drop_index('idx_content_project_status', table_name='generated_content')
    op.drop_index(op.f('ix_generated_content_id'), table_name='generated_content')
    op.drop_table('generated_content')

    op.drop_index(op.f('ix_reddit_accounts_username'), table_name='reddit_accounts')
    op.drop_index(op.f('ix_reddit_accounts_id'), table_name='reddit_accounts')
    op.drop_table('reddit_accounts')

    op.drop_index('idx_opp_composite', table_name='opportunities')
    op.drop_index('idx_opp_project_status', table_name='opportunities')
    op.drop_index(op.f('ix_opportunities_id'), table_name='opportunities')
    op.drop_table('opportunities')

    op.drop_index(op.f('ix_projects_name'), table_name='projects')
    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    op.drop_table('projects')
