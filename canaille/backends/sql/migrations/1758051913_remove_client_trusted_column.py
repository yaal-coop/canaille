"""Remove client.trusted column.

Revision ID: 1758051913
Revises: 1755869767
Create Date: 2025-01-17 08:58:33.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1758051913"
down_revision = "1755869767"
branch_labels = None
depends_on = None


def upgrade():
    """Remove the trusted column from client table."""
    with op.batch_alter_table("client") as batch_op:
        batch_op.drop_column("trusted")


def downgrade():
    """Re-add the trusted column to client table."""
    with op.batch_alter_table("client") as batch_op:
        batch_op.add_column(sa.Column("trusted", sa.Boolean(), nullable=True))
