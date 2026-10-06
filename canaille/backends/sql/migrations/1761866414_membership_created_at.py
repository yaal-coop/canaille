"""membership created_at.

Revision ID: 1761866414
Revises: 1761862795
Create Date: 2025-10-31 00:46:54.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

from canaille.backends.sql.utils import is_mysql

# revision identifiers, used by Alembic.
revision: str = "1761866414"
down_revision: str | None = "1761862795"
branch_labels: str | Sequence[str] | None = ()
depends_on: str | Sequence[str] | None = None


# Members are ordered by creation date, so MySQL needs sub-second precision.
CREATED_AT = sa.DateTime(timezone=True).with_variant(
    mysql.DATETIME(fsp=6), "mysql", "mariadb"
)


def current_timestamp():
    # MySQL computes CURRENT_TIMESTAMP in the session time zone,
    # but dates are stored in UTC.
    if is_mysql(op.get_bind().dialect):
        return sa.text("(UTC_TIMESTAMP(6))")
    return sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    # Step 1: Add created_at column as nullable
    with op.batch_alter_table("membership_association_table", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                CREATED_AT,
                nullable=True,
                server_default=current_timestamp(),
            )
        )

    # Step 2: Fill created_at for existing rows
    op.execute(f"""
        UPDATE membership_association_table
        SET created_at = {current_timestamp()}
        WHERE created_at IS NULL
    """)

    # Step 3: Make created_at non-nullable and drop index
    with op.batch_alter_table("membership_association_table", schema=None) as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=CREATED_AT,
            existing_server_default=current_timestamp(),
            nullable=False,
        )
        batch_op.drop_column("index")


def downgrade() -> None:
    # Step 1: Add back index column
    with op.batch_alter_table("membership_association_table", schema=None) as batch_op:
        batch_op.add_column(sa.Column("index", sa.INTEGER(), nullable=True))

    # Step 2: Set index values (arbitrary order based on created_at)
    # This is best-effort since we can't recover the exact original order
    # We use row_number() window function to assign sequential indices per group
    if is_mysql(op.get_bind().dialect):
        op.execute("""
            UPDATE membership_association_table t
            JOIN (
                SELECT user_id, group_id,
                       ROW_NUMBER() OVER (PARTITION BY group_id ORDER BY created_at) - 1 as new_index
                FROM membership_association_table
            ) n
            ON t.user_id = n.user_id AND t.group_id = n.group_id
            SET t.`index` = n.new_index
        """)
    else:
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
        batch_op.alter_column("index", existing_type=sa.INTEGER(), nullable=False)
        batch_op.drop_column("created_at")
