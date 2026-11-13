"""Add OpenID Connect Back-Channel Logout support.

Revision ID: 1794562361
Revises: 1793118531
Create Date: 2026-11-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1794562361"
down_revision: str | None = "1793118531"
branch_labels: str | Sequence[str] | None = ()
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the back-channel logout client metadata and the session identifiers."""
    op.add_column(
        "client",
        sa.Column("backchannel_logout_uri", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "client",
        sa.Column("backchannel_logout_session_required", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "authorization_code",
        sa.Column("sid", sa.String(length=255), nullable=True),
    )
    op.add_column("token", sa.Column("sid", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_token_sid"), "token", ["sid"])


def downgrade() -> None:
    """Remove the back-channel logout client metadata and the session identifiers."""
    op.drop_index(op.f("ix_token_sid"), table_name="token")
    op.drop_column("token", "sid")
    op.drop_column("authorization_code", "sid")
    op.drop_column("client", "backchannel_logout_session_required")
    op.drop_column("client", "backchannel_logout_uri")
