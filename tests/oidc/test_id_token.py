import datetime
from urllib.parse import parse_qs
from urllib.parse import urlsplit

import time_machine
from authlib.jose import jwt

from canaille.app import models

from . import client_credentials


def test_nominal_case(
    testclient, logged_user, client, keypair, trusted_client, backend, caplog
):
    assert not backend.query(models.Consent)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile email groups address phone",
            nonce="somenonce",
            tos_uri="https://client.test/tos",
            policy_uri="https://client.test/policy",
            redirect_uri="https://client.test/redirect1",
        ),
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile email groups address phone",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    assert claims.header["kid"]
    assert claims["sub"] == logged_user.user_name
    assert claims["name"] == logged_user.formatted_name
    assert claims["aud"] == [client.client_id, trusted_client.client_id]

    for consent in backend.query(models.Consent, client=client, subject=logged_user):
        backend.delete(consent)


def test_auth_time(
    testclient,
    user,
    client,
    keypair,
    backend,
):
    """Check that the ID token contains the user authentication time."""
    auth_time = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
    with time_machine.travel(auth_time, tick=False):
        res = testclient.get("/login")
        res.form["login"] = "user"
        res = res.form.submit().follow()
        res.form["password"] = "correct horse battery staple"
        res = res.form.submit()

    with time_machine.travel(
        datetime.datetime(2025, 1, 1, 12, 1, tzinfo=datetime.timezone.utc), tick=False
    ):
        res = testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type="code",
                client_id=client.client_id,
                scope="openid profile email groups address phone",
                nonce="somenonce",
                tos_uri="https://client.test/tos",
                policy_uri="https://client.test/policy",
                redirect_uri="https://client.test/redirect1",
                max_age=15000,
            ),
        )
        res = res.form.submit(name="answer", value="accept", status=302)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]

    with time_machine.travel(
        datetime.datetime(2025, 1, 1, 12, 2, tzinfo=datetime.timezone.utc), tick=False
    ):
        res = testclient.post(
            "/oauth/token",
            params=dict(
                grant_type="authorization_code",
                code=code,
                scope="openid profile email groups address phone",
                redirect_uri=client.redirect_uris[0],
            ),
            headers={"Authorization": f"Basic {client_credentials(client)}"},
        )

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    id_token_auth_time = datetime.datetime.fromtimestamp(
        claims["auth_time"], tz=datetime.timezone.utc
    )
    assert id_token_auth_time == auth_time

    backend.delete(backend.get(models.Consent))


def test_auth_time_update(
    testclient,
    user,
    client,
    keypair,
    backend,
):
    """Certification test 'oidcc-max-age-10000'.

    This test calls the authorization endpoint test twice. The first time it includes max_age=15000 (so that the OP is required to return auth_time in the id_token). The second time it includes max_age=10000, and the authorization server must not request that the user logs in. The test verifies that auth_time and sub are consistent between the id_tokens from the first and second authorizations.
    """
    auth_time = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
    with time_machine.travel(auth_time, tick=False):
        res = testclient.get("/login")
        res.form["login"] = "user"
        res = res.form.submit().follow()
        res.form["password"] = "correct horse battery staple"
        res = res.form.submit()

    with time_machine.travel(
        datetime.datetime(2025, 1, 1, 12, 1, tzinfo=datetime.timezone.utc), tick=False
    ):
        res = testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type="code",
                client_id=client.client_id,
                scope="openid profile email groups address phone",
                nonce="somenonce",
                tos_uri="https://client.test/tos",
                policy_uri="https://client.test/policy",
                redirect_uri="https://client.test/redirect1",
                max_age=15000,
            ),
            status=200,
        )

        res = res.form.submit(name="answer", value="accept", status=302)

    params = parse_qs(urlsplit(res.location).query)
    code1 = params["code"][0]

    with time_machine.travel(
        datetime.datetime(2025, 1, 1, 12, 2, tzinfo=datetime.timezone.utc), tick=False
    ):
        res = testclient.post(
            "/oauth/token",
            params=dict(
                grant_type="authorization_code",
                code=code1,
                scope="openid profile email groups address phone",
                redirect_uri=client.redirect_uris[0],
            ),
            headers={"Authorization": f"Basic {client_credentials(client)}"},
            status=200,
        )

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    id_token_1_auth_time = datetime.datetime.fromtimestamp(
        claims["auth_time"], tz=datetime.timezone.utc
    )
    assert id_token_1_auth_time == auth_time

    backend.delete(backend.get(models.Consent))

    with time_machine.travel(
        datetime.datetime(2025, 1, 1, 12, 3, tzinfo=datetime.timezone.utc), tick=False
    ):
        res = testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type="code",
                client_id=client.client_id,
                scope="openid profile email groups address phone",
                nonce="somenonce",
                tos_uri="https://client.test/tos",
                policy_uri="https://client.test/policy",
                redirect_uri="https://client.test/redirect1",
            ),
            status=200,
        )

    res = res.form.submit(name="answer", value="accept", status=302)
    params = parse_qs(urlsplit(res.location).query)
    code2 = params["code"][0]

    assert code1 != code2

    with time_machine.travel(
        datetime.datetime(2025, 1, 1, 12, 4, tzinfo=datetime.timezone.utc), tick=False
    ):
        res = testclient.post(
            "/oauth/token",
            params=dict(
                grant_type="authorization_code",
                code=code2,
                scope="openid profile email groups address phone",
                redirect_uri=client.redirect_uris[0],
                max_age=10000,
            ),
            headers={"Authorization": f"Basic {client_credentials(client)}"},
            status=200,
        )

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    id_token_2_auth_time = datetime.datetime.fromtimestamp(
        claims["auth_time"], tz=datetime.timezone.utc
    )
    assert id_token_2_auth_time == auth_time
