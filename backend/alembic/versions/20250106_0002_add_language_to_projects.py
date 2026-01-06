"""Add language and posting settings to projects table

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add language column to projects table
    op.add_column(
        'projects',
        sa.Column('language', sa.String(length=10), nullable=True)
    )
    # Create index for language column for faster filtering
    op.create_index('ix_projects_language', 'projects', ['language'], unique=False)

    # Add negative_keywords column if it doesn't exist
    op.add_column(
        'projects',
        sa.Column('negative_keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]')
    )

    # Add posting mode settings
    op.add_column(
        'projects',
        sa.Column('posting_mode', sa.String(length=20), nullable=False, server_default='rotate')
    )
    op.add_column(
        'projects',
        sa.Column('preferred_account_id', sa.Integer(), nullable=True)
    )
    op.add_column(
        'projects',
        sa.Column('last_used_account_index', sa.Integer(), nullable=False, server_default='0')
    )

    # Add foreign key constraint for preferred_account_id
    op.create_foreign_key(
        'fk_projects_preferred_account',
        'projects',
        'reddit_accounts',
        ['preferred_account_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_projects_preferred_account', 'projects', type_='foreignkey')
    op.drop_column('projects', 'last_used_account_index')
    op.drop_column('projects', 'preferred_account_id')
    op.drop_column('projects', 'posting_mode')
    op.drop_index('ix_projects_language', table_name='projects')
    op.drop_column('projects', 'language')
    op.drop_column('projects', 'negative_keywords')
