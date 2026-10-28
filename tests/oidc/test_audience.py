import datetime
from urllib.parse import parse_qs
from urllib.parse import urlsplit

from joserfc import jwt
from werkzeug.security import gen_salt

from canaille.app import models
from canaille.oidc.jose import registry

from . import client_credentials


def get_tokens(testclient, client):
    """Get tokens for ``client`` with the authorization code flow."""
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            redirect_uri=client.redirect_uris[0],
        ),
        status=200,
    )
    res = res.form.submit(name="answer", value="accept", status=302)
    code = parse_qs(urlsplit(res.location).query)["code"][0]

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    return res.json


def introspect(testclient, client, access_token):
    res = testclient.post(
        "/oauth/introspect",
        params=dict(token=access_token),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    return res.json


def test_client_without_audience(testclient, logged_user, client, server_jwk, backend):
    """A client without audience is the audience of its own tokens."""
    client.audience = []
    backend.save(client)

    tokens = get_tokens(testclient, client)
    for token in (tokens["access_token"], tokens["id_token"]):
        claims = jwt.decode(token, server_jwk, registry=registry).claims
        assert claims["aud"] == [client.client_id]

    payload = introspect(testclient, client, tokens["access_token"])
    assert payload["active"]
    assert payload["aud"] == [client.client_id]


def test_client_audience_self_reference(
    testclient, logged_user, client, trusted_client, server_jwk, backend
):
    """A client stored in its own audience is not repeated in the tokens."""
    client.audience = [client, trusted_client]
    backend.save(client)

    tokens = get_tokens(testclient, client)
    claims = jwt.decode(tokens["id_token"], server_jwk, registry=registry).claims
    assert claims["aud"] == [client.client_id, trusted_client.client_id]


def test_token_without_audience_introspection(testclient, client, user, backend):
    """A client can introspect its tokens that were issued without audience."""
    token = models.Token(
        token_id=gen_salt(48),
        access_token=gen_salt(48),
        client=client,
        subject=user,
        audience=[],
        scope=["openid"],
        issue_date=datetime.datetime.now(datetime.UTC),
        lifetime=3600,
    )
    backend.save(token)

    payload = introspect(testclient, client, token.access_token)
    assert payload["active"]
    assert payload["aud"] == [client.client_id]

    backend.delete(token)


def test_audience_suggestions_skip_the_client(
    testclient, logged_admin, client, trusted_client, backend
):
    """The edited client is not suggested for its own audience."""
    client.audience = []
    backend.save(client)

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    form = res.forms["clienteditform"]
    form["audience-query"] = "client"
    res = form.submit("audience-search")

    suggestions = [
        button.attrib["value"]
        for button in res.pyquery('button[name="audience-suggestions"]')
    ]
    assert trusted_client.id in suggestions
    assert client.id not in suggestions
