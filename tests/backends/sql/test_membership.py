import datetime

import pytest
from sqlalchemy import select
from sqlalchemy import text

from canaille.backends.sql.models.core import Membership


def test_membership_date_defaults_to_utc(request, backend, admin, foo_group):
    """A membership inserted without a date gets the current UTC date."""
    if backend.engine.dialect.name == "postgresql":
        request.applymarker(
            pytest.mark.xfail(
                reason="TZDateTime reads PostgreSQL dates in the session time zone as UTC",
                strict=False,
            )
        )
    backend.db_session.execute(
        text(
            "INSERT INTO membership_association_table (user_id, group_id) "
            "VALUES (:user_id, :group_id)"
        ),
        {"user_id": admin.id, "group_id": foo_group.id},
    )

    created_at = backend.db_session.execute(
        select(Membership.created_at).where(
            Membership.user_id == admin.id, Membership.group_id == foo_group.id
        )
    ).scalar()

    now = datetime.datetime.now(datetime.UTC)
    assert abs(now - created_at) < datetime.timedelta(minutes=1)
