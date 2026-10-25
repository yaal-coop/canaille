import datetime

from werkzeug.security import gen_salt

from canaille.app import models

from . import client_credentials


def remove_use_oidc(testclient, backend, user):
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"].remove(
        "use_oidc"
    )
    backend.reload(user)


def test_password_grant_without_use_oidc(testclient, user, client, backend):
    """A user without USE_OIDC gets the same error as with a wrong password."""
    remove_use_oidc(testclient, backend, user)

    responses = [
        testclient.post(
            "/oauth/token",
            params=dict(
                grant_type="password",
                username="user",
                password=password,
                scope="openid profile",
            ),
            headers={"Authorization": f"Basic {client_credentials(client)}"},
            status=400,
        ).json
        for password in ("correct horse battery staple", "wrong password")
    ]
    assert responses[0] == responses[1]
    assert not backend.query(models.Token, client=client, subject=user)


def test_code_exchange_without_use_oidc(testclient, user, client, backend):
    """A user who lost USE_OIDC gets no token for their authorization code."""
    code = models.AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code=gen_salt(48),
        client=client,
        subject=user,
        redirect_uri="https://client.test/redirect1",
        response_type="code",
        scope=["openid", "profile"],
        issue_date=datetime.datetime.now(datetime.UTC),
        lifetime=300,
    )
    backend.save(code)
    remove_use_oidc(testclient, backend, user)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code.code,
            redirect_uri=code.redirect_uri,
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json["error"] == "invalid_grant"
    assert not backend.query(models.Token, client=client, subject=user)

    backend.delete(code)


def test_refresh_without_use_oidc(testclient, user, client, token, backend):
    """A user who lost USE_OIDC cannot refresh their tokens."""
    remove_use_oidc(testclient, backend, user)

    res = testclient.post(
        "/oauth/token",
        params=dict(grant_type="refresh_token", refresh_token=token.refresh_token),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json["error"] == "invalid_grant"


def test_tokens_without_use_oidc(testclient, user, client, token, backend):
    """The tokens of a user who lost USE_OIDC are refused."""
    testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
        status=200,
    )

    remove_use_oidc(testclient, backend, user)

    testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
        status=401,
    )
