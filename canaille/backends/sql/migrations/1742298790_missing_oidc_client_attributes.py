"""Missing oidc client attributes.

Revision ID: 1742298790
Revises: 1742033764
Create Date: 2025-03-18 12:53:10.926898

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1742298790"
down_revision: str | None = "1742033764"
branch_labels: str | Sequence[str] | None = ()
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "client",
        sa.Column("token_endpoint_auth_signing_alg", sa.String(), nullable=True),
    )
    op.add_column(
        "client", sa.Column("sector_identifier_uri", sa.String(), nullable=True)
    )
    op.add_column("client", sa.Column("subject_type", sa.String(), nullable=True))
    op.add_column("client", sa.Column("application_type", sa.String(), nullable=True))
    op.add_column(
        "client", sa.Column("id_token_signed_response_alg", sa.String(), nullable=True)
    )
    op.add_column(
        "client",
        sa.Column("id_token_encrypted_response_alg", sa.String(), nullable=True),
    )
    op.add_column(
        "client",
        sa.Column("id_token_encrypted_response_enc", sa.String(), nullable=True),
    )
    op.add_column(
        "client", sa.Column("userinfo_signed_response_alg", sa.String(), nullable=True)
    )
    op.add_column(
        "client",
        sa.Column("userinfo_encrypted_response_alg", sa.String(), nullable=True),
    )
    op.add_column(
        "client",
        sa.Column("userinfo_encrypted_response_enc", sa.String(), nullable=True),
    )
    op.add_column("client", sa.Column("default_max_age", sa.Integer(), nullable=True))
    op.add_column("client", sa.Column("require_auth_time", sa.Boolean(), nullable=True))
    op.add_column("client", sa.Column("default_acr_values", sa.JSON(), nullable=True))
    op.add_column("client", sa.Column("initiate_login_uri", sa.String(), nullable=True))
    op.add_column(
        "client", sa.Column("request_object_signing_alg", sa.String(), nullable=True)
    )
    op.add_column(
        "client", sa.Column("request_object_encryption_alg", sa.String(), nullable=True)
    )
    op.add_column(
        "client", sa.Column("request_object_encryption_enc", sa.String(), nullable=True)
    )
    op.add_column("client", sa.Column("request_uris", sa.JSON(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("client", "request_uris")
    op.drop_column("client", "request_object_encryption_enc")
    op.drop_column("client", "request_object_encryption_alg")
    op.drop_column("client", "request_object_signing_alg")
    op.drop_column("client", "initiate_login_uri")
    op.drop_column("client", "default_acr_values")
    op.drop_column("client", "require_auth_time")
    op.drop_column("client", "default_max_age")
    op.drop_column("client", "userinfo_encrypted_response_enc")
    op.drop_column("client", "userinfo_encrypted_response_alg")
    op.drop_column("client", "userinfo_signed_response_alg")
    op.drop_column("client", "id_token_encrypted_response_enc")
    op.drop_column("client", "id_token_encrypted_response_alg")
    op.drop_column("client", "id_token_signed_response_alg")
    op.drop_column("client", "application_type")
    op.drop_column("client", "subject_type")
    op.drop_column("client", "sector_identifier_uri")
    op.drop_column("client", "token_endpoint_auth_signing_alg")
    # ### end Alembic commands ###
