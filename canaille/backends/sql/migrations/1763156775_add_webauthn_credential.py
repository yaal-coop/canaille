"""Add WebAuthn credential support.

Revision ID: 1763156775
Revises: 1761866414
Create Date: 2025-11-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from canaille.backends.sql.utils import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "1763156775"
down_revision: str | None = "1761866414"
branch_labels: str | Sequence[str] | None = ()
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create webauthn_credential table."""
    op.create_table(
        "webauthn_credential",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("aaguid", sa.LargeBinary(), nullable=True),
        sa.Column("transports", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            TZDateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_used_at", TZDateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_webauthn_credential_user_id_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_webauthn_credential"),
        sa.UniqueConstraint(
            "credential_id", name="uq_webauthn_credential_credential_id"
        ),
    )
    op.create_index(
        "ix_webauthn_credential_credential_id",
        "webauthn_credential",
        ["credential_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop webauthn_credential table."""
    op.drop_index(
        "ix_webauthn_credential_credential_id", table_name="webauthn_credential"
    )
    op.drop_table("webauthn_credential")
