"""rename all foreign keys to follow naming convention.

Revision ID: 1761846634
Revises: 1761846138
Create Date: 2025-10-30 18:50:34.311497

This migration ensures all foreign keys follow the naming convention:
fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s

For databases created before the naming convention was introduced,
this will rename foreign keys. For databases created after, this
migration will have no effect (foreign keys already have correct names).
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import inspect

revision: str = "1761846634"
down_revision: str | None = "1761846138"
branch_labels: str | Sequence[str] | None = ()
depends_on: str | Sequence[str] | None = None


def _get_expected_fk_name(table_name, column_name, referred_table):
    """Generate the expected FK name according to naming convention."""
    return f"fk_{table_name}_{column_name}_{referred_table}"


def _rename_fks_postgresql(table_name, foreign_keys, inspector):
    """Rename foreign keys using PostgreSQL's RENAME CONSTRAINT."""
    existing_fks = inspector.get_foreign_keys(table_name)

    for column_name, referred_table in foreign_keys:
        expected_name = _get_expected_fk_name(table_name, column_name, referred_table)

        for fk in existing_fks:  # pragma: no cover
            if (
                column_name in fk["constrained_columns"]
                and fk["referred_table"] == referred_table
            ):
                old_name = fk.get("name")
                if old_name and old_name != expected_name:
                    op.execute(
                        f'ALTER TABLE "{table_name}" '
                        f'RENAME CONSTRAINT "{old_name}" TO "{expected_name}"'
                    )
                break


def upgrade() -> None:
    """Rename all foreign keys to follow the naming convention using ALTER TABLE RENAME CONSTRAINT."""
    bind = op.get_bind()
    inspector = inspect(bind)

    tables_fks = [
        ("authorization_code", [("client_id", "client"), ("subject_id", "user")]),
        ("consent", [("client_id", "client"), ("subject_id", "user")]),
        ("token", [("client_id", "client"), ("subject_id", "user")]),
        ("membership_association_table", [("user_id", "user"), ("group_id", "group")]),
        (
            "client_audience_association_table",
            [("audience_id", "client"), ("client_id", "client")],
        ),
        (
            "token_audience_association_table",
            [("token_id", "token"), ("client_id", "client")],
        ),
    ]

    for table_name, fks in tables_fks:
        _rename_fks_postgresql(table_name, fks, inspector)


def downgrade() -> None:
    pass
