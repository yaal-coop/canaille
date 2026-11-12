import ldap
import pytest

from canaille.app import models


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE_OIDC"] = {"ENABLE_OIDC": True}
    return configuration


def raw_value(backend, instance, attribute):
    with backend.connection() as conn:
        _, attributes = conn.search_s(
            instance.dn, ldap.SCOPE_BASE, "(objectClass=*)", [attribute]
        )[0]
    return attributes[attribute][0].decode()


def test_secrets_are_encrypted(app, backend, user):
    """Client secrets and one-time passcode secrets are encrypted in the directory."""
    client = models.Client(client_id="client", client_secret="client-secret")
    backend.save(client)

    assert raw_value(backend, client, "oauthClientSecret").startswith("enc:v1:")
    assert raw_value(backend, user, "oathSecret").startswith("enc:v1:")

    backend.reload(client)
    backend.reload(user)
    assert client.client_secret == "client-secret"
    assert user.secret_token == "fefe9b10"

    backend.delete(client)


def test_clear_text_secrets(app, backend, user):
    """Secrets stored before encryption are read as is."""
    with backend.connection() as conn:
        conn.modify_s(user.dn, [(ldap.MOD_REPLACE, "oathSecret", [b"clear"])])

    backend.reload(user)
    assert user.secret_token == "clear"
