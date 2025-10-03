from joserfc import jwt

from canaille.app import models
from canaille.commands import cli
from canaille.oidc.jose import server_jwks


def test_generate_registration_token_default(cli_runner, testclient, backend):
    """Test default registration token generation and usage."""
    res = cli_runner.invoke(cli, ["jwt", "registration"])
    assert res.exit_code == 0, res.output

    token = res.stdout.strip()
    jwks = server_jwks(include_inactive=False)
    decoded = jwt.decode(token, jwks.keys[0])

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
    decoded = jwt.decode(token, jwks.keys[0])

    assert decoded.claims["scope"] == "client:manage"
    assert decoded.claims["sub"] == client.client_id

    res = testclient.get(
        f"/oauth/register/{client.client_id}",
        headers={"Authorization": f"Bearer {token}"},
        status=200,
    )

    assert res.json["client_id"] == client.client_id


def test_generate_registration_token_custom_expiration(cli_runner, testclient, backend):
    """Test registration token generation with custom lifetime."""
    res = cli_runner.invoke(cli, ["jwt", "registration", "--lifetime", "3600"])
    assert res.exit_code == 0

    token = res.stdout.strip()
    jwks = server_jwks(include_inactive=False)
    decoded = jwt.decode(token, jwks.keys[0])

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
