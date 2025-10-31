"""membership created_at.

Revision ID: 1761866414
Revises: 1761862795
Create Date: 2025-10-31 00:46:54.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1761866414"
down_revision: str | None = "1761862795"
branch_labels: str | Sequence[str] | None = ()
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Step 1: Add created_at column as nullable
    with op.batch_alter_table("membership_association_table", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )

    # Step 2: Fill created_at for existing rows
    op.execute("""
        UPDATE membership_association_table
        SET created_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL
    """)

    # Step 3: Make created_at non-nullable and drop index
    with op.batch_alter_table("membership_association_table", schema=None) as batch_op:
        batch_op.alter_column("created_at", nullable=False)
        batch_op.drop_column("index")


def downgrade() -> None:
    # Step 1: Add back index column
    with op.batch_alter_table("membership_association_table", schema=None) as batch_op:
        batch_op.add_column(sa.Column("index", sa.INTEGER(), nullable=True))

    # Step 2: Set index values (arbitrary order based on created_at)
    # This is best-effort since we can't recover the exact original order
    # We use row_number() window function to assign sequential indices per group
    op.execute("""
        WITH numbered AS (
            SELECT user_id, group_id,
                   ROW_NUMBER() OVER (PARTITION BY group_id ORDER BY created_at) - 1 as new_index
            FROM membership_association_table
        )
        UPDATE membership_association_table
        SET "index" = n.new_index
        FROM numbered n
        WHERE membership_association_table.user_id = n.user_id
          AND membership_association_table.group_id = n.group_id
    """)

    # Step 3: Make index non-nullable and drop created_at
    with op.batch_alter_table("membership_association_table", schema=None) as batch_op:
        batch_op.alter_column("index", nullable=False)
        batch_op.drop_column("created_at")
