"""add_buyer_coordinates

Revision ID: 3b10bb821b3d
Revises: 00ef7277e811
Create Date: 2026-10-14 17:01:47.353675

Adds nullable latitude, longitude, and coordinate_source fields to the buyers table
for GPS-based nearest-buyer search (STEP 11H.5).
Preserves all existing buyer records with NULL coordinates until verified coordinates
are available.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b10bb821b3d'
down_revision: Union[str, Sequence[str], None] = '00ef7277e811'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add nullable coordinate fields and spatial index to buyers table."""
    op.add_column(
        'buyers',
        sa.Column(
            'latitude',
            sa.Numeric(precision=9, scale=6),
            nullable=True,
            comment='WGS84 latitude coordinate (~0.11m precision)'
        )
    )
    op.add_column(
        'buyers',
        sa.Column(
            'longitude',
            sa.Numeric(precision=9, scale=6),
            nullable=True,
            comment='WGS84 longitude coordinate (~0.11m precision)'
        )
    )
    op.add_column(
        'buyers',
        sa.Column(
            'coordinate_source',
            sa.String(length=100),
            nullable=True,
            comment='Provenance or source authority of verified coordinates'
        )
    )
    op.create_index(
        'idx_buyers_coordinates',
        'buyers',
        ['latitude', 'longitude'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema: Remove coordinate fields and spatial index from buyers table."""
    op.drop_index('idx_buyers_coordinates', table_name='buyers')
    op.drop_column('buyers', 'coordinate_source')
    op.drop_column('buyers', 'longitude')
    op.drop_column('buyers', 'latitude')
