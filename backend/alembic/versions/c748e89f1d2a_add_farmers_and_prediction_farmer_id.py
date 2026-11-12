"""add_farmers_and_prediction_farmer_id

Revision ID: c748e89f1d2a
Revises: 3b10bb821b3d
Create Date: 2026-11-01 17:15:00.000000

Creates the 'farmers' table for authentic farmer identity and adds nullable 'farmer_id'
foreign key with ON DELETE SET NULL to 'prediction_history' with a composite index
on ('farmer_id', 'created_at') for strict farmer-specific dashboard data isolation.
All 53 existing legacy prediction records remain 100% preserved with farmer_id = NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c748e89f1d2a'
down_revision: Union[str, Sequence[str], None] = '3b10bb821b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create farmers table and add nullable farmer_id to prediction_history."""
    # 1. Create 'farmers' table
    op.create_table(
        'farmers',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False, comment='Surrogate UUID primary key for farmer entity'),
        sa.Column('username', sa.String(length=100), nullable=False, comment='Unique login username or handle'),
        sa.Column('password_hash', sa.String(length=255), nullable=False, comment='Cryptographically salted and hashed password'),
        sa.Column('full_name', sa.String(length=150), nullable=True, comment='Farmer personal full name'),
        sa.Column('farm_name', sa.String(length=150), nullable=True, comment='Name of the agricultural holding or farm'),
        sa.Column('village', sa.String(length=100), nullable=True, comment='Village or locality location'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False, comment='Active account status flag'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Account creation timestamp in UTC'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_farmers')),
    )
    op.create_index(op.f('ix_farmers_username'), 'farmers', ['username'], unique=True)

    # 2. Add nullable 'farmer_id' column to 'prediction_history'
    op.add_column(
        'prediction_history',
        sa.Column(
            'farmer_id',
            sa.UUID(),
            nullable=True,
            comment='Owner farmer UUID (nullable for legacy/standalone predictions)'
        )
    )

    # 3. Create foreign key constraint with ON DELETE SET NULL
    op.create_foreign_key(
        op.f('fk_prediction_history_farmer_id_farmers'),
        'prediction_history',
        'farmers',
        ['farmer_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # 4. Create composite index on (farmer_id, created_at)
    op.create_index(
        'idx_pred_farmer_created',
        'prediction_history',
        ['farmer_id', 'created_at'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema: drop composite index, foreign key, farmer_id column, and farmers table."""
    op.drop_index('idx_pred_farmer_created', table_name='prediction_history')
    op.drop_constraint(op.f('fk_prediction_history_farmer_id_farmers'), 'prediction_history', type_='foreignkey')
    op.drop_column('prediction_history', 'farmer_id')
    op.drop_index(op.f('ix_farmers_username'), table_name='farmers')
    op.drop_table('farmers')
