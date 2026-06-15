import datetime
from urllib.parse import parse_qs
from urllib.parse import urlsplit

from joserfc import jwt
from werkzeug.security import gen_salt

from canaille.app import models
from canaille.oidc.jose import registry
from canaille.oidc.provider import setup_oauth

from . import client_credentials


def test_token_default_expiration_date(
    testclient, logged_user, client, server_jwk, backend
):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile email groups address phone",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode.lifetime == 300

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile email groups address phone",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    assert res.json["expires_in"] == 864000

    access_token = res.json["access_token"]
    token = backend.get(models.Token, access_token=access_token)
    assert token.lifetime == 864000

    claims = jwt.decode(
        access_token,
        server_jwk,
        registry=registry,
    )
    assert claims.claims["exp"] - claims.claims["iat"] == 864000

    id_token = res.json["id_token"]
    claims = jwt.decode(
        id_token,
        server_jwk,
        registry=registry,
    )
    assert claims.claims["exp"] - claims.claims["iat"] == 3600

    consents = backend.query(models.Consent, client=client, subject=logged_user)
    for consent in consents:
        backend.delete(consent)


def test_token_custom_expiration_date(
    testclient, logged_user, client, server_jwk, backend
):
    testclient.app.config["OAUTH2_TOKEN_EXPIRES_IN"] = {
        "authorization_code": 1000,
        "implicit": 2000,
        "password": 3000,
        "client_credentials": 4000,
        "urn:ietf:params:oauth:grant-type:jwt-bearer": 5000,
    }
    setup_oauth(testclient.app)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile email groups address phone",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode.lifetime == 300

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile email groups address phone",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    assert res.json["expires_in"] == 1000

    access_token = res.json["access_token"]
    token = backend.get(models.Token, access_token=access_token)
    assert token.lifetime == 1000

    claims = jwt.decode(
        access_token,
        server_jwk,
        registry=registry,
    )
    assert claims.claims["exp"] - claims.claims["iat"] == 1000

    id_token = res.json["id_token"]
    claims = jwt.decode(
        id_token,
        server_jwk,
        registry=registry,
    )
    lifetime = claims.claims["exp"] - claims.claims["iat"]
    assert lifetime == 3600

    consents = backend.query(models.Consent, client=client, subject=logged_user)
    for consent in consents:
        backend.delete(consent)


def test_expiry_checks_tolerate_missing_lifetime(testclient, client, user, backend):
    """Tokens and codes without a recorded lifetime are treated as expired."""
    now = datetime.datetime.now(datetime.timezone.utc)

    token = models.Token(
        token_id=gen_salt(48),
        access_token=gen_salt(48),
        audience=[client],
        client=client,
        subject=user,
        refresh_token=gen_salt(48),
        scope=["openid", "profile"],
        issue_date=now,
    )
    backend.save(token)
    assert token.lifetime is None
    assert token.is_expired() is True
    assert token.expire_date == token.issue_date
    assert token.get_expires_at() == token.get_issued_at()
    backend.delete(token)

    code = models.AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code=gen_salt(48),
        client=client,
        subject=user,
        redirect_uri="https://client.test/redirect1",
        response_type="code",
        scope=["openid", "profile"],
        nonce="nonce",
        issue_date=now,
    )
    backend.save(code)
    assert code.lifetime is None
    assert code.is_expired() is True
    backend.delete(code)
