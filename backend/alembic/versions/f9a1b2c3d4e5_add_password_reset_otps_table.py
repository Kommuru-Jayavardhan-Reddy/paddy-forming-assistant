"""add_password_reset_otps_table

Revision ID: f9a1b2c3d4e5
Revises: e8f91a2b3c4d
Create Date: 2026-11-06 09:30:00.000000

Creates 'public.password_reset_otps' table to securely store hashed OTP verification
records, attempt counts, expiration dates, and single-use password reset tokens.
Fully idempotent: safely handles repeated upgrade and downgrade cycles.
"""
from typing import Sequence, Union
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

logger = logging.getLogger("alembic.runtime.migration")

# revision identifiers, used by Alembic.
revision: str = 'f9a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = 'e8f91a2b3c4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Checks if a table already exists in public schema."""
    bind = op.get_bind()
    res = bind.execute(sa.text("""
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = :t;
    """), {"t": table_name}).scalar()
    return bool(res)


def upgrade() -> None:
    if not table_exists("password_reset_otps"):
        op.create_table(
            "password_reset_otps",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
                comment="Primary UUID key for OTP reset session",
            ),
            sa.Column(
                "farmer_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("farmers.id", ondelete="CASCADE"),
                nullable=True,
                comment="Associated farmer ID if registered",
            ),
            sa.Column(
                "mobile_number",
                sa.String(25),
                nullable=False,
                comment="Raw mobile number entered during request",
            ),
            sa.Column(
                "normalized_mobile",
                sa.String(25),
                nullable=False,
                comment="E.164 normalized phone identity (+91XXXXXXXXXX)",
            ),
            sa.Column(
                "otp_hash",
                sa.String(255),
                nullable=False,
                comment="Cryptographically hashed OTP (Argon2id)",
            ),
            sa.Column(
                "reset_token_hash",
                sa.String(255),
                nullable=True,
                comment="Hash of verified reset token permitted to update password",
            ),
            sa.Column(
                "attempts",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=False,
                comment="Number of incorrect OTP verification attempts",
            ),
            sa.Column(
                "max_attempts",
                sa.Integer(),
                server_default=sa.text("5"),
                nullable=False,
                comment="Maximum allowed incorrect attempts before session lockout",
            ),
            sa.Column(
                "is_verified",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
                comment="Flag indicating OTP was successfully verified",
            ),
            sa.Column(
                "is_used",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
                comment="Flag indicating password reset completed (single use)",
            ),
            sa.Column(
                "expires_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="OTP expiration timestamp in UTC (5 minutes from creation)",
            ),
            sa.Column(
                "last_resend_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="Timestamp of latest OTP dispatch for cooldown enforcement",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
                comment="Record creation timestamp in UTC",
            ),
        )
        op.create_index(
            "ix_password_reset_otps_farmer_id",
            "password_reset_otps",
            ["farmer_id"],
        )
        op.create_index(
            "ix_password_reset_otps_normalized_mobile",
            "password_reset_otps",
            ["normalized_mobile"],
        )
        op.create_index(
            "ix_password_reset_otps_reset_token_hash",
            "password_reset_otps",
            ["reset_token_hash"],
        )
        logger.info("Successfully created 'password_reset_otps' table and indexes.")


def downgrade() -> None:
    if table_exists("password_reset_otps"):
        op.drop_index("ix_password_reset_otps_reset_token_hash", table_name="password_reset_otps")
        op.drop_index("ix_password_reset_otps_normalized_mobile", table_name="password_reset_otps")
        op.drop_index("ix_password_reset_otps_farmer_id", table_name="password_reset_otps")
        op.drop_table("password_reset_otps")
        logger.info("Successfully dropped 'password_reset_otps' table.")

