import json

from joserfc import jwt

from canaille.app import models
from canaille.commands import cli
from canaille.oidc.jose import registry
from canaille.oidc.jose import server_jwks


def test_generate_registration_token_default(cli_runner, testclient, backend):
    """Test default registration token generation and usage."""
    res = cli_runner.invoke(cli, ["jwt", "registration"])
    assert res.exit_code == 0, res.output

    token = res.stdout.strip()
    jwks = server_jwks(include_inactive=False)
    decoded = jwt.decode(
        token,
        jwks.keys[0],
        registry=registry,
    )

    assert decoded.claims["scope"] == "client:register"

    client_id = decoded.claims["sub"]
    assert not backend.get(models.Client, client_id=client_id)

    res = testclient.post_json(
        "/oauth/register",
        {
            "redirect_uris": ["https://client.test/callback"],
            "client_name": "Test Client",
        },
        headers={"Authorization": f"Bearer {token}"},
        status=201,
    )

    assert res.json["client_id"] == client_id


def test_generate_management(cli_runner, testclient, backend, client):
    """Test management token generation for an existing client."""
    res = cli_runner.invoke(cli, ["jwt", "management", client.client_id])
    assert res.exit_code == 0

    token = res.stdout.strip()
    jwks = server_jwks(include_inactive=False)
    decoded = jwt.decode(
        token,
        jwks.keys[0],
        registry=registry,
    )

    assert decoded.claims["scope"] == "client:manage"
    assert decoded.claims["sub"] == client.client_id

    res = testclient.get(
        f"/oauth/register/{client.client_id}",
        headers={"Authorization": f"Bearer {token}"},
        status=200,
    )

    assert res.json["client_id"] == client.client_id


def test_generate_registration_token_with_client_id(cli_runner, testclient, backend):
    """A registration token can pin the identifier of the future client."""
    res = cli_runner.invoke(cli, ["jwt", "registration", "--client-id", "my-client"])
    assert res.exit_code == 0, res.output

    token = res.stdout.strip()
    jwks = server_jwks(include_inactive=False)
    decoded = jwt.decode(
        token,
        jwks.keys[0],
        registry=registry,
    )

    assert decoded.claims["sub"] == "my-client"

    res = testclient.post_json(
        "/oauth/register",
        {
            "redirect_uris": ["https://client.test/callback"],
            "client_name": "Test Client",
        },
        headers={"Authorization": f"Bearer {token}"},
        status=201,
    )

    assert res.json["client_id"] == "my-client"
    backend.delete(backend.get(models.Client, client_id="my-client"))


def test_generate_registration_token_with_registered_client_id(
    cli_runner, testclient, backend, client
):
    """A registration token for an already registered client would be useless."""
    res = cli_runner.invoke(
        cli, ["jwt", "registration", "--client-id", client.client_id]
    )
    assert res.exit_code == 1
    assert "already registered" in res.output


def test_generate_registration_token_with_invalid_client_id(cli_runner, testclient):
    """Identifiers that would be percent-encoded in an URL are refused."""
    res = cli_runner.invoke(cli, ["jwt", "registration", "--client-id", "foo/bar"])
    assert res.exit_code == 2
    assert "unreserved URL characters" in res.output


def test_generate_management_token_for_unregistered_client(cli_runner, testclient):
    """A management token for an unknown client would be useless."""
    res = cli_runner.invoke(cli, ["jwt", "management", "invalid"])
    assert res.exit_code == 1
    assert "not registered" in res.output


def test_generate_registration_token_json(cli_runner, testclient, backend):
    """The JSON output tells where to use the token, and for which client."""
    res = cli_runner.invoke(cli, ["jwt", "registration", "--json"])
    assert res.exit_code == 0, res.output

    payload = json.loads(res.stdout)

    # The registration endpoint is the one advertised by the discovery document.
    metadata = testclient.get("/.well-known/oauth-authorization-server").json
    assert payload["registration_endpoint"] == metadata["registration_endpoint"]

    jwks = server_jwks(include_inactive=False)
    decoded = jwt.decode(
        payload["initial_access_token"],
        jwks.keys[0],
        registry=registry,
    )
    assert decoded.claims["sub"] == payload["client_id"]


def test_generate_management_token_json(cli_runner, testclient, backend, client):
    """The JSON output tells which URL the management token applies to."""
    res = cli_runner.invoke(cli, ["jwt", "management", client.client_id, "--json"])
    assert res.exit_code == 0, res.output

    payload = json.loads(res.stdout)
    assert payload["client_id"] == client.client_id
    assert payload["registration_client_uri"].endswith(
        f"/oauth/register/{client.client_id}"
    )

    res = testclient.get(
        f"/oauth/register/{client.client_id}",
        headers={"Authorization": f"Bearer {payload['registration_access_token']}"},
        status=200,
    )

    # The management output is a subset of the RFC7592 response.
    assert res.json["registration_client_uri"] == payload["registration_client_uri"]


def test_generate_registration_token_custom_expiration(cli_runner, testclient, backend):
    """Test registration token generation with custom lifetime."""
    res = cli_runner.invoke(cli, ["jwt", "registration", "--lifetime", "3600"])
    assert res.exit_code == 0

    token = res.stdout.strip()
    jwks = server_jwks(include_inactive=False)
    decoded = jwt.decode(
        token,
        jwks.keys[0],
        registry=registry,
    )

    exp_diff = decoded.claims["exp"] - decoded.claims["iat"]
    assert exp_diff == 3600

    client_id = decoded.claims["sub"]

    res = testclient.post_json(
        "/oauth/register",
        {
            "redirect_uris": ["https://client.test/callback"],
            "client_name": "Test Client",
        },
        headers={"Authorization": f"Bearer {token}"},
        status=201,
    )

    assert res.json["client_id"] == client_id


def test_generate_registration_token_without_server_name(cli_runner, testclient):
    """Test registration token generation fails without SERVER_NAME."""
    testclient.app.config["SERVER_NAME"] = None

    res = cli_runner.invoke(cli, ["jwt", "registration"])
    assert res.exit_code == 1
    assert "SERVER_NAME" in res.output


def test_generate_management_token_without_server_name(
    cli_runner, testclient, backend, client
):
    """Test management token generation fails without SERVER_NAME."""
    testclient.app.config["SERVER_NAME"] = None

    res = cli_runner.invoke(cli, ["jwt", "management", client.client_id])
    assert res.exit_code == 1
    assert "SERVER_NAME" in res.output
