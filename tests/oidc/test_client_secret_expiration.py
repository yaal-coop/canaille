import datetime
import logging

from . import client_credentials


def test_expired_secret_cannot_authenticate(testclient, client, backend, caplog):
    """Clients cannot use an expired secret at the token endpoint."""
    client.client_secret_expires_at = datetime.datetime.now(
        datetime.timezone.utc
    ) - datetime.timedelta(days=1)
    backend.save(client)
    assert client.secret_expired

    res = testclient.post(
        "/oauth/token",
        params=dict(grant_type="client_credentials"),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=401,
    )

    assert res.json["error"] == "invalid_client"
    assert (
        "canaille",
        logging.SECURITY,
        f"Client {client.client_id} authentication attempt with a secret "
        f"expired since {client.client_secret_expires_at}",
    ) in caplog.record_tuples


def test_expired_secret_cannot_authenticate_with_client_secret_post(
    testclient, client, backend
):
    """The client_secret_post method is guarded the same way as client_secret_basic."""
    client.token_endpoint_auth_method = "client_secret_post"
    client.client_secret_expires_at = datetime.datetime.now(
        datetime.timezone.utc
    ) - datetime.timedelta(days=1)
    backend.save(client)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="client_credentials",
            client_id=client.client_id,
            client_secret=client.client_secret,
        ),
        status=401,
    )

    assert res.json["error"] == "invalid_client"


def test_future_expiration_can_authenticate(testclient, client, backend):
    """A secret expiring in the future is still valid."""
    client.client_secret_expires_at = datetime.datetime.now(
        datetime.timezone.utc
    ) + datetime.timedelta(days=1)
    backend.save(client)
    assert not client.secret_expired

    testclient.post(
        "/oauth/token",
        params=dict(grant_type="client_credentials"),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )


def test_edit_secret_expiration(testclient, client, logged_admin, backend):
    """Administrators can set and unset the secret expiration date."""
    assert not client.client_secret_expires_at

    expiration = datetime.datetime.now(datetime.timezone.utc).replace(
        second=0, microsecond=0
    ) + datetime.timedelta(days=30)

    res = testclient.get("/admin/client/edit/" + client.client_id)
    res.forms["clienteditform"]["client_secret_expires_at"] = expiration.strftime(
        "%Y-%m-%d %H:%M"
    )
    res = res.forms["clienteditform"].submit(status=302, name="action", value="edit")
    assert ("success", "The client has been edited.") in res.flashes

    backend.reload(client)
    assert client.client_secret_expires_at == expiration
    assert not client.secret_expired

    res = res.follow()
    res.forms["clienteditform"]["client_secret_expires_at"] = ""
    res = res.forms["clienteditform"].submit(status=302, name="action", value="edit")

    backend.reload(client)
    assert client.client_secret_expires_at is None


def test_new_client_secret(testclient, client, logged_admin, backend, caplog):
    """Renewing the secret of a client clears its expiration date."""
    old_secret = client.client_secret
    client.client_secret_expires_at = datetime.datetime.now(
        datetime.timezone.utc
    ) - datetime.timedelta(days=1)
    backend.save(client)

    res = testclient.get("/admin/client/edit/" + client.client_id)
    res = res.forms["clienteditform"].submit(
        status=302, name="action", value="new-client-secret"
    )
    assert (
        "success",
        "The client secret has been renewed. The new secret does not expire.",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        f"Renewed the secret of client {client.client_id} by {logged_admin.id}",
    ) in caplog.record_tuples

    backend.reload(client)
    assert client.client_secret != old_secret
    assert client.client_secret_expires_at is None
    assert not client.secret_expired

    testclient.post(
        "/oauth/token",
        params=dict(grant_type="client_credentials"),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )


def test_expired_secret_is_displayed(testclient, client, logged_admin, backend):
    """Expired secrets are reported on the client page and in the client list."""
    res = testclient.get("/admin/client/edit/" + client.client_id)
    res.mustcontain(no="Expired secret")
    res = testclient.get("/admin/client")
    res.mustcontain(no="The secret of this application has expired")

    client.client_secret_expires_at = datetime.datetime.now(
        datetime.timezone.utc
    ) - datetime.timedelta(days=1)
    backend.save(client)

    res = testclient.get("/admin/client/edit/" + client.client_id)
    res.mustcontain("Expired secret")
    res = testclient.get("/admin/client")
    res.mustcontain("The secret of this application has expired")


def test_secret_expiration_is_serialized_as_a_timestamp(testclient, client, backend):
    """The RFC7591 client information uses timestamps, and 0 when there is no expiration."""
    assert client.client_info["client_secret_expires_at"] == 0

    expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        days=1
    )
    client.client_secret_expires_at = expiration
    backend.save(client)
    assert client.client_info["client_secret_expires_at"] == int(expiration.timestamp())
