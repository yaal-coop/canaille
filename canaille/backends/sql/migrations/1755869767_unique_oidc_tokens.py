"""Unique OIDC tokens.

Revision ID: 1755869767
Revises: 1745234836
Create Date: 2025-08-22 15:36:07.150344

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1755869767"
down_revision: str | None = "1745234836"
branch_labels: str | Sequence[str] | None = ()
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("token") as batch_op:
        batch_op.create_unique_constraint("uq_token_refresh_token", ["refresh_token"])
        batch_op.create_unique_constraint("uq_token_access_token", ["access_token"])


def downgrade() -> None:
    with op.batch_alter_table("token") as batch_op:
        batch_op.drop_constraint("uq_token_refresh_token", type_="unique")
        batch_op.drop_constraint("uq_token_access_token", type_="unique")
