from urllib.parse import parse_qs
from urllib.parse import urlsplit

from authlib.jose import jwt
from canaille.models import User
from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Token


def test_oauth_hybrid(testclient, slapd_connection, user, client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code token",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
        status=200,
    )
    assert "text/html" == res.content_type, res.json

    res.form["login"] = user.formatted_name[0]
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)

    res = res.follow(status=200)
    assert "text/html" == res.content_type, res.json

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).fragment)

    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code)
    assert authcode is not None

    access_token = params["access_token"][0]
    token = Token.get(access_token=access_token)
    assert token is not None

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"


def test_oidc_hybrid(
    testclient, slapd_connection, logged_user, client, keypair, other_client
):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code id_token token",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
    )
    assert "text/html" == res.content_type, res.json

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).fragment)

    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code)
    assert authcode is not None

    access_token = params["access_token"][0]
    token = Token.get(access_token=access_token)
    assert token is not None

    id_token = params["id_token"][0]
    claims = jwt.decode(id_token, keypair[1])
    assert logged_user.user_name[0] == claims["sub"]
    assert logged_user.formatted_name[0] == claims["name"]
    assert [client.client_id, other_client.client_id] == claims["aud"]

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"
