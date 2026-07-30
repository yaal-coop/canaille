"""Client secret never expires is null.

Revision ID: 1785442300
Revises: 1763156775
Create Date: 2026-07-30 22:11:40.000000

"""

import datetime
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

import canaille.backends.sql.utils

# revision identifiers, used by Alembic.
revision: str = "1785442300"
down_revision: str | None = "1763156775"
branch_labels: str | Sequence[str] | None = ()
depends_on: str | Sequence[str] | None = None

client = sa.table(
    "client",
    sa.column(
        "client_secret_expires_at",
        canaille.backends.sql.utils.TZDateTime(timezone=True),
    ),
)

EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


def upgrade() -> None:
    """Clients registered dynamically stored the epoch instead of NULL.

    RFC7591 uses a 0 ``client_secret_expires_at`` to tell that the secret never
    expires, and this was converted as a datetime instead of being left empty.
    """
    op.execute(
        client.update()
        .where(client.c.client_secret_expires_at == EPOCH)
        .values(client_secret_expires_at=None)
    )


def downgrade() -> None:
    """Nothing to do.

    Clients whose secret never expires are indistinguishable from the clients
    that got their expiration date emptied by the upgrade.
    """
