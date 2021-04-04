import json
from canaille.commands import client as client_command
from canaille.models import Client


def test_get(testclient, slapd_connection, client):
    runner = testclient.app.test_cli_runner()
    result = runner.invoke(
        client_command,
        args=[
            "get",
            "--id",
            client.oauthClientID,
        ],
    )
    json_output = json.loads(result.output)
    assert json_output == {
        "id": client.oauthClientID,
        "name": "Some client",
        "contact": "contact@mydomain.tld",
        "uri": "https://mydomain.tld",
        "redirect_uri": [
            "https://mydomain.tld/redirect1",
            "https://mydomain.tld/redirect2",
        ],
        "logo": "https://mydomain.tld/logo.png",
        "issue_date": client.oauthIssueDate,
        "secret": client.oauthClientSecret,
        "grant_type": [
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
        ],
        "response_type": ["code", "token", "id_token"],
        "scope": ["openid", "profile"],
        "terms_of_service": "https://mydomain.tld/tos",
        "policy": "https://mydomain.tld/policy",
        "jwk_uri": "https://mydomain.tld/jwk",
        "token_endpoint_auth_method": "client_secret_basic",
    }


def test_create(testclient, slapd_connection):
    runner = testclient.app.test_cli_runner()
    runner.invoke(
        client_command,
        args=[
            "create",
            "--id=id",
            "--name=name",
            "--contact=contact@mydomain.tld",
            "--uri=https://mydomain.tld",
            "--redirect-uri=https://mydomain.tld/redirect",
            "--logo-uri=https://mydomain.tld/logo.png",
            "--secret=secret",
            "--secret-exp-date=01-01-1970",
            "--grant-type=authorization_code",
            "--response-type=code",
            "--scope=openid profile",
            "--tos-uri=https://mydomain.tld/tos",
            "--policy-uri=https://mydomain.tld/policy",
            "--jwk=0",
            "--jwk-uri=https://mydomain.tld/jwk",
            "--token-endpoint-auth-method=none",
            "--software-id=software",
            "--software-version=0",
        ],
    )

    c = Client.filter(id="id")
    assert c.id == "id"
    assert c.name == "name"
    assert c.contact == "contact@mydomain.tld"
    assert c.uri == "https://mydomain.tld"
    assert c.redirect_uri == "https://mydomain.tld/redirect"
    assert c.logo == "https:/mydomain.tld/logo.png"
    assert c.secret == "secret"
    assert c.secret_exp_date == "01-01-1970"
    assert c.grant_type == "authorization_code"
    assert c.response_type == "code"
    assert c.scope == "openid profile"
    assert c.tos_uri == "https://mydomain.tld/tos"
    assert c.policy_uri == "https://mydomain.tld/policy"
    assert c.jwk == "0"
    assert c.jwk_uri == "https://mydomain.tld/jwk"
    assert c.token_endpoint_auth_method == "none"
    assert c.software_id == "software"
    assert c.software_version == "0"


def test_edit(testclient, slapd_connection):
    runner = testclient.app.test_cli_runner()
    runner.invoke(
        client_command,
        args=[
            "create",
            "--id=id",
            "--name=name",
            "--contact=contact@mydomain.tld",
            "--uri=https://mydomain.tld",
            "--redirect-uri=https://mydomain.tld/redirect",
            "--logo-uri=https://mydomain.tld/logo.png",
            "--secret=secret",
            "--secret-exp-date=01-01-1970",
            "--grant-type=authorization_code",
            "--response-type=code",
            "--scope=openid profile",
            "--tos-uri=https://mydomain.tld/tos",
            "--policy-uri=https://mydomain.tld/policy",
            "--jwk=0",
            "--jwk-uri=https://mydomain.tld/jwk",
            "--token-endpoint-auth-method=none",
            "--software-id=software",
            "--software-version=0",
        ],
    )

    c = Client.filter(id="id")
    assert c.id == "id"
    assert c.name == "name"
    assert c.contact == "contact@mydomain.tld"
    assert c.uri == "https://mydomain.tld"
    assert c.redirect_uri == "https://mydomain.tld/redirect"
    assert c.logo == "https:/mydomain.tld/logo.png"
    assert c.secret == "secret"
    assert c.secret_exp_date == "01-01-1970"
    assert c.grant_type == "authorization_code"
    assert c.response_type == "code"
    assert c.scope == "openid profile"
    assert c.tos_uri == "https://mydomain.tld/tos"
    assert c.policy_uri == "https://mydomain.tld/policy"
    assert c.jwk == "0"
    assert c.jwk_uri == "https://mydomain.tld/jwk"
    assert c.token_endpoint_auth_method == "none"
    assert c.software_id == "software"
    assert c.software_version == "0"
