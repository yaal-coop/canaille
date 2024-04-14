from urllib.parse import parse_qs
from urllib.parse import urlsplit

from authlib.jose import jwt

from canaille.app import models
from canaille.oidc.oauth import setup_oauth

from . import client_credentials


def test_token_default_expiration_date(
    testclient, logged_user, client, keypair, backend
):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile email groups address phone",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode.lifetime == 84400

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

    claims = jwt.decode(access_token, keypair[1])
    assert claims["exp"] - claims["iat"] == 864000

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    assert claims["exp"] - claims["iat"] == 3600

    consents = backend.query(models.Consent, client=client, subject=logged_user)
    for consent in consents:
        backend.delete(consent)


def test_token_custom_expiration_date(
    testclient, logged_user, client, keypair, backend
):
    testclient.app.config["OAUTH2_TOKEN_EXPIRES_IN"] = {
        "authorization_code": 1000,
        "implicit": 2000,
        "password": 3000,
        "client_credentials": 4000,
        "urn:ietf:params:oauth:grant-type:jwt-bearer": 5000,
    }
    testclient.app.config["CANAILLE_OIDC"]["JWT"]["EXP"] = 6000
    setup_oauth(testclient.app)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile email groups address phone",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode.lifetime == 84400

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

    claims = jwt.decode(access_token, keypair[1])
    assert claims["exp"] - claims["iat"] == 1000

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    assert claims["exp"] - claims["iat"] == 6000

    consents = backend.query(models.Consent, client=client, subject=logged_user)
    for consent in consents:
        backend.delete(consent)
