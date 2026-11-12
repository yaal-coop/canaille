import pytest
import sqlalchemy as sa

from canaille.app import models


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE_OIDC"] = {"ENABLE_OIDC": True}
    return configuration


def raw_value(backend, table, column, id):
    table = sa.table(table, sa.column("id"), sa.column(column))
    return backend.db_session.execute(
        sa.select(table.c[column]).where(table.c.id == id)
    ).scalar()


def test_secrets_are_encrypted(app, backend, user):
    """Client secrets and one-time passcode secrets are encrypted in the database."""
    client = models.Client(client_id="client", client_secret="client-secret")
    backend.save(client)

    stored_secret = raw_value(backend, "client", "client_secret", client.id)
    assert stored_secret.startswith("enc:v1:")
    stored_token = raw_value(backend, "user", "secret_token", user.id)
    assert stored_token.startswith("enc:v1:")

    backend.reload(client)
    backend.reload(user)
    assert client.client_secret == "client-secret"
    assert user.secret_token == "fefe9b10"

    backend.delete(client)


def test_clear_text_secrets(app, backend, user):
    """Secrets stored before encryption are read as is."""
    table = sa.table("user", sa.column("id"), sa.column("secret_token"))
    backend.db_session.execute(
        sa.update(table).where(table.c.id == user.id).values(secret_token="clear")
    )
    backend.db_session.commit()

    backend.reload(user)
    assert user.secret_token == "clear"
