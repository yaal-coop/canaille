"""Add multiple owners for groups.

Revision ID: 1793118531
Revises: 1793102055
Create Date: 2026-10-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from canaille.backends.sql.utils import TZDateTime
from canaille.backends.sql.utils import is_mysql

# revision identifiers, used by Alembic.
revision: str = "1793118531"
down_revision: str | None = "1793102055"
branch_labels: str | Sequence[str] | None = ()
depends_on: str | Sequence[str] | None = None

group = sa.table("group", sa.column("id"), sa.column("owner_id"))
group_ownership = sa.table(
    "group_ownership",
    sa.column("owner_id"),
    sa.column("group_id"),
    sa.column("created_at"),
)


def current_timestamp():
    # MySQL computes CURRENT_TIMESTAMP in the session time zone,
    # but dates are stored in UTC.
    if is_mysql(op.get_bind().dialect):
        return sa.text("(UTC_TIMESTAMP(6))")
    return sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    """Move the group owners into the group_ownership table."""
    op.create_table(
        "group_ownership",
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            TZDateTime(timezone=True),
            server_default=current_timestamp(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["group.id"],
            name="fk_group_ownership_group_id_group",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["user.id"],
            name="fk_group_ownership_owner_id_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("owner_id", "group_id", name="pk_group_ownership"),
    )

    op.execute(
        sa.insert(group_ownership).from_select(
            ["owner_id", "group_id"],
            sa.select(group.c.owner_id, group.c.id).where(
                group.c.owner_id.is_not(None)
            ),
        )
    )

    with op.batch_alter_table("group", schema=None) as batch_op:
        batch_op.drop_constraint(
            batch_op.f("fk_group_owner_id_user"), type_="foreignkey"
        )
        batch_op.drop_column("owner_id")


def downgrade() -> None:
    """Keep the first owner of each group, and drop the group_ownership table."""
    with op.batch_alter_table("group", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "owner_id",
                sa.String().with_variant(sa.String(255), "mysql", "mariadb"),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_group_owner_id_user"),
            "user",
            ["owner_id"],
            ["id"],
            ondelete="SET NULL",
        )

    first_owner = (
        sa.select(group_ownership.c.owner_id)
        .where(group_ownership.c.group_id == group.c.id)
        .order_by(group_ownership.c.created_at)
        .limit(1)
        .scalar_subquery()
    )
    op.execute(sa.update(group).values(owner_id=first_owner))

    op.drop_table("group_ownership")
