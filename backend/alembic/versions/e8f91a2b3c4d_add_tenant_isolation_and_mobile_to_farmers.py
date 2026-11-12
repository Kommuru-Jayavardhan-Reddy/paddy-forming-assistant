"""add_tenant_isolation_and_mobile_to_farmers

Revision ID: e8f91a2b3c4d
Revises: c748e89f1d2a
Create Date: 2026-11-02 12:40:00.000000

Adds mobile_number, normalized_mobile (E.164 nullable), role, schema_name, encrypted_db_secret, and updated_at
to 'public.farmers' with strict uniqueness and check constraints for database-enforced multi-tenant isolation.
Fully idempotent: safely handles repeated upgrade -> downgrade -> upgrade cycles without data loss.
Preserves existing farmer records and historical catalog integrity with zero dummy data fabrication.
"""
from typing import Sequence, Union
import logging

from alembic import op
import sqlalchemy as sa

logger = logging.getLogger("alembic.runtime.migration")

# revision identifiers, used by Alembic.
revision: str = 'e8f91a2b3c4d'
down_revision: Union[str, Sequence[str], None] = 'c748e89f1d2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Checks if a column already exists in public table."""
    bind = op.get_bind()
    res = bind.execute(sa.text("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = :t AND column_name = :c;
    """), {"t": table_name, "c": column_name}).scalar()
    return bool(res)


def index_exists(index_name: str) -> bool:
    """Checks if an index already exists in public schema."""
    bind = op.get_bind()
    res = bind.execute(sa.text("""
        SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = :idx;
    """), {"idx": index_name}).scalar()
    return bool(res)


def constraint_exists(table_name: str, constraint_partial: str) -> bool:
    """Checks if a constraint matching pattern exists on table."""
    bind = op.get_bind()
    res = bind.execute(sa.text("""
        SELECT 1 FROM pg_constraint 
        WHERE conrelid = ('public.' || :t)::regclass AND conname LIKE ('%' || :c || '%');
    """), {"t": table_name, "c": constraint_partial}).scalar()
    return bool(res)


def drop_constraint_if_exists(table_name: str, constraint_partial: str):
    """Safely drops any constraint on table matching pattern."""
    bind = op.get_bind()
    rows = bind.execute(sa.text("""
        SELECT conname FROM pg_constraint 
        WHERE conrelid = ('public.' || :t)::regclass AND conname LIKE ('%' || :c || '%');
    """), {"t": table_name, "c": constraint_partial}).fetchall()
    for row in rows:
        bind.execute(sa.text(f'ALTER TABLE "{table_name}" DROP CONSTRAINT IF EXISTS "{row[0]}";'))


def upgrade() -> None:
    """
    Idempotent upgrade:
    Adds columns only if they do not already exist (e.g. preserved by a previous safe downgrade).
    Re-creates unique indexes and check constraints idempotently.
    """
    # 1. Add columns idempotently (nullable, zero fake data invented)
    if not column_exists('farmers', 'mobile_number'):
        op.add_column(
            'farmers',
            sa.Column('mobile_number', sa.String(length=20), nullable=True, comment='Raw phone number provided at registration')
        )
    if not column_exists('farmers', 'normalized_mobile'):
        op.add_column(
            'farmers',
            sa.Column('normalized_mobile', sa.String(length=20), nullable=True, comment='Strict E.164 normalized mobile identity (nullable for legacy/unverified accounts)')
        )
    if not column_exists('farmers', 'role'):
        op.add_column(
            'farmers',
            sa.Column('role', sa.String(length=20), nullable=False, server_default='farmer', comment="Role: 'farmer' or 'admin'")
        )
    if not column_exists('farmers', 'schema_name'):
        op.add_column(
            'farmers',
            sa.Column('schema_name', sa.String(length=63), nullable=True, comment='Dedicated tenant PostgreSQL schema (NULL for admin)')
        )
    if not column_exists('farmers', 'encrypted_db_secret'):
        op.add_column(
            'farmers',
            sa.Column('encrypted_db_secret', sa.String(length=500), nullable=True, comment='Authenticated ciphertext of per-tenant database secret')
        )
    if not column_exists('farmers', 'updated_at'):
        op.add_column(
            'farmers',
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Timestamp of last update in UTC')
        )

    # 2. Create unique indexes idempotently
    if not index_exists('ix_farmers_normalized_mobile'):
        op.create_index(op.f('ix_farmers_normalized_mobile'), 'farmers', ['normalized_mobile'], unique=True)
    if not index_exists('ix_farmers_schema_name'):
        op.create_index(op.f('ix_farmers_schema_name'), 'farmers', ['schema_name'], unique=True)

    # 3. Create check constraints idempotently
    if not constraint_exists('farmers', 'chk_farmers_role_valid'):
        op.create_check_constraint(
            'chk_farmers_role_valid',
            'farmers',
            "role IN ('farmer', 'admin')"
        )
    if not constraint_exists('farmers', 'chk_farmers_e164_mobile'):
        op.create_check_constraint(
            'chk_farmers_e164_mobile',
            'farmers',
            "normalized_mobile IS NULL OR normalized_mobile ~ '^\\+[1-9][0-9]{7,14}$'"
        )
    if not constraint_exists('farmers', 'chk_farmers_schema_format'):
        op.create_check_constraint(
            'chk_farmers_schema_format',
            'farmers',
            "(role = 'admin' AND schema_name IS NULL) OR (role = 'farmer' AND (schema_name IS NULL OR schema_name ~ '^farmer_[a-f0-9]{16}$'))"
        )


def downgrade() -> None:
    """
    Safe downgrade strategy:
    1. If security-related columns contain data, downgrade MUST REFUSE to proceed.
       Dropping constraints and indexes while data is populated leaves data unprotected
       and unconstrained, violating the security baseline.
    2. If no security data is populated, safely and cleanly drops constraints, indexes,
       and columns to return the schema to revision 'c748e89f1d2a'.
    """
    bind = op.get_bind()

    # Inspect if any security-critical data exists in 'farmers'
    has_security_data = False
    row = None
    if column_exists('farmers', 'mobile_number') or column_exists('farmers', 'schema_name'):
        row = bind.execute(sa.text("""
            SELECT 
                COUNT(*) AS total_rows,
                COUNT(*) FILTER (WHERE mobile_number IS NOT NULL) AS has_mobile,
                COUNT(*) FILTER (WHERE normalized_mobile IS NOT NULL) AS has_norm_mobile,
                COUNT(*) FILTER (WHERE schema_name IS NOT NULL) AS has_schema,
                COUNT(*) FILTER (WHERE encrypted_db_secret IS NOT NULL) AS has_secret,
                COUNT(*) FILTER (WHERE role != 'farmer') AS has_custom_roles
            FROM farmers;
        """)).mappings().one()

        if (row['has_mobile'] > 0 or 
            row['has_norm_mobile'] > 0 or 
            row['has_schema'] > 0 or 
            row['has_secret'] > 0 or 
            row['has_custom_roles'] > 0):
            has_security_data = True

    if has_security_data:
        raise RuntimeError(
            f"DOWNGRADE BLOCKED: Table 'farmers' contains populated security-critical data "
            f"(mobile={row['has_mobile']}, norm_mobile={row['has_norm_mobile']}, "
            f"schema={row['has_schema']}, secret={row['has_secret']}, custom_roles={row['has_custom_roles']}). "
            f"Downgrading would remove E.164 phone normalization, tenant schema isolation, and role check constraints, "
            f"leaving existing farmer records unconstrained or orphaned. "
            f"Rollback aborted safely to protect data integrity and tenant security posture."
        )

    # If NO security data is populated (clean table or pre-migration state), safely remove constraints, indexes, columns
    drop_constraint_if_exists('farmers', 'chk_farmers_schema_format')
    drop_constraint_if_exists('farmers', 'chk_farmers_e164_mobile')
    drop_constraint_if_exists('farmers', 'chk_farmers_role_valid')

    if index_exists('ix_farmers_schema_name'):
        op.drop_index(op.f('ix_farmers_schema_name'), table_name='farmers')
    if index_exists('ix_farmers_normalized_mobile'):
        op.drop_index(op.f('ix_farmers_normalized_mobile'), table_name='farmers')

    if column_exists('farmers', 'updated_at'):
        op.drop_column('farmers', 'updated_at')
    if column_exists('farmers', 'encrypted_db_secret'):
        op.drop_column('farmers', 'encrypted_db_secret')
    if column_exists('farmers', 'schema_name'):
        op.drop_column('farmers', 'schema_name')
    if column_exists('farmers', 'role'):
        op.drop_column('farmers', 'role')
    if column_exists('farmers', 'normalized_mobile'):
        op.drop_column('farmers', 'normalized_mobile')
    if column_exists('farmers', 'mobile_number'):
        op.drop_column('farmers', 'mobile_number')
