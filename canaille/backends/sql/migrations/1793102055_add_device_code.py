"""Add device code support (RFC 8628).

Revision ID: 1793102055
Revises: 1792862550
Create Date: 2026-10-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from canaille.backends.sql.utils import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "1793102055"
down_revision: str | None = "1792862550"
branch_labels: str | Sequence[str] | None = ()
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create device_code table."""
    op.create_table(
        "device_code",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created", TZDateTime(timezone=True), nullable=True),
        sa.Column("last_modified", TZDateTime(timezone=True), nullable=True),
        sa.Column("device_code_id", sa.String(length=255), nullable=True),
        sa.Column("device_code", sa.String(length=255), nullable=True),
        sa.Column("user_code", sa.String(length=255), nullable=True),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=True),
        sa.Column("scope", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("issue_date", TZDateTime(timezone=True), nullable=True),
        sa.Column("lifetime", sa.Integer(), nullable=True),
        sa.Column("last_polled", TZDateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["client.id"],
            name="fk_device_code_client_id_client",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["user.id"],
            name="fk_device_code_subject_id_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_device_code"),
        sa.UniqueConstraint("device_code", name="uq_device_code_device_code"),
    )
    op.create_index(
        "ix_device_code_user_code",
        "device_code",
        ["user_code"],
        unique=False,
    )


def downgrade() -> None:
    """Drop device_code table."""
    op.drop_index("ix_device_code_user_code", table_name="device_code")
    op.drop_table("device_code")
