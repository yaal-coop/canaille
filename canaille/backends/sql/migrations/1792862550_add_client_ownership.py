"""Add client ownership.

Revision ID: 1792862550
Revises: 1785442300
Create Date: 2026-10-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1792862550"
down_revision: str | None = "1785442300"
branch_labels: str | Sequence[str] | None = ()
depends_on: str | Sequence[str] | None = None

COLUMNS = ["client_id", "user_id", "group_id"]


def upgrade():
    """Add client owners association table."""
    op.create_table(
        "client_owner_association_table",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "client_id",
            sa.String(36),
            sa.ForeignKey("client.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "group_id",
            sa.String(36),
            sa.ForeignKey("group.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("index", sa.Integer, nullable=False),
        sa.CheckConstraint(
            "(user_id IS NULL) <> (group_id IS NULL)", name="user_or_group"
        ),
    )
    for column in COLUMNS:
        op.create_index(
            f"ix_client_owner_association_table_{column}",
            "client_owner_association_table",
            [column],
        )


def downgrade():
    """Remove client owners association table, with its indexes."""
    op.drop_table("client_owner_association_table")
