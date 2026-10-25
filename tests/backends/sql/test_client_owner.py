import pytest
from sqlalchemy import insert
from sqlalchemy.exc import DBAPIError

from canaille.app import models
from canaille.backends.sql.models.oidc import ClientOwner


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE_OIDC"] = {"ENABLE_OIDC": True}
    return configuration


def test_client_owner_cannot_be_none():
    """A client owner is a user or a group."""
    with pytest.raises(ValueError):
        ClientOwner.of(None)


def test_client_owner_is_a_user_or_a_group(app, backend, admin, foo_group):
    """A client owner row references either a user or a group."""
    client = models.Client(client_id="client", client_name="Client")
    backend.save(client)
    for row_id, user_id, group_id in (
        ("neither", None, None),
        ("both", admin.id, foo_group.id),
    ):
        with pytest.raises(DBAPIError):
            backend.db_session.execute(
                insert(ClientOwner).values(
                    id=row_id,
                    client_id=client.id,
                    user_id=user_id,
                    group_id=group_id,
                    index=0,
                )
            )
        backend.db_session.rollback()

    backend.delete(client)
