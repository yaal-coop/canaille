"""Add group ownership and invitation support.

Revision ID: 1760000353
Create Date: 2025-10-09

"""

import sqlalchemy as sa
from alembic import op

revision = "1760000353"
down_revision = "1758051913"


def upgrade():
    """Add group owner field and group_invitation table."""
    op.add_column("group", sa.Column("owner_id", sa.String(), nullable=True))


def downgrade():
    """Remove group owner field and group_invitation table."""
    op.drop_column("group", "owner_id")
