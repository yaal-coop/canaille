from urllib.parse import parse_qs
from urllib.parse import urlsplit

from joserfc import jwt

from canaille.app import models
from canaille.oidc.jose import registry
from canaille.oidc.provider import compute_amr_values
from tests.core.test_auth_otp import generate_otp

from . import client_credentials


def test_amr_password_only(testclient, user, client, server_jwk, backend):
    """Test that AMR contains only 'pwd' for password-only authentication."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password"]

    res = testclient.get("/login")
    res.form["login"] = "user"
    res = res.form.submit().follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
    )
    res = res.form.submit(name="answer", value="accept", status=302)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, server_jwk, registry=registry)
    assert claims.claims["amr"] == ["pwd"]

    for consent in backend.query(models.Consent, client=client, subject=user):
        backend.delete(consent)


def test_amr_password_and_otp(testclient, user, client, server_jwk, backend):
    """Test that AMR contains 'pwd', 'otp', and 'mfa' for password + OTP authentication."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "otp"]

    res = testclient.get("/login")
    res.form["login"] = "user"
    res = res.form.submit().follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit().follow()

    totp_period = int(
        testclient.app.config["CANAILLE"]["TOTP_LIFETIME"].total_seconds()
    )
    res.form["otp"] = generate_otp("TOTP", user.secret_token, totp_period=totp_period)
    res = res.form.submit()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
    )
    res = res.form.submit(name="answer", value="accept", status=302)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, server_jwk, registry=registry)
    assert set(claims.claims["amr"]) == {"pwd", "otp", "mfa"}

    for consent in backend.query(models.Consent, client=client, subject=user):
        backend.delete(consent)


def test_amr_password_and_sms(smtpd, testclient, user, client, server_jwk, backend):
    """Test that AMR contains 'pwd', 'sms', and 'mfa' for password + SMS authentication."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "sms"]

    res = testclient.get("/login")
    res.form["login"] = "user"
    res = res.form.submit().follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit().follow()

    backend.reload(user)
    res.form["otp"] = user.one_time_password
    res = res.form.submit()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
    )
    res = res.form.submit(name="answer", value="accept", status=302)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, server_jwk, registry=registry)
    assert set(claims.claims["amr"]) == {"pwd", "sms", "mca", "mfa"}

    for consent in backend.query(models.Consent, client=client, subject=user):
        backend.delete(consent)


def test_amr_password_and_email(smtpd, testclient, user, client, server_jwk, backend):
    """Test that AMR contains 'pwd', 'mca', and 'mfa' for password + email authentication."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = [
        "password",
        "email",
    ]

    res = testclient.get("/login")
    res.form["login"] = "user"
    res = res.form.submit().follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit().follow()

    backend.reload(user)
    res.form["otp"] = user.one_time_password
    res = res.form.submit()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
    )
    res = res.form.submit(name="answer", value="accept", status=302)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, server_jwk, registry=registry)
    assert set(claims.claims["amr"]) == {"pwd", "mca", "mfa"}

    for consent in backend.query(models.Consent, client=client, subject=user):
        backend.delete(consent)


def test_compute_amr_values_none():
    """Test compute_amr_values with None returns None."""
    assert compute_amr_values(None) is None


def test_compute_amr_values_empty_list():
    """Test compute_amr_values with empty list returns None."""
    assert compute_amr_values([]) is None


def test_compute_amr_values_unknown_method():
    """Test compute_amr_values with unknown method returns None."""
    assert compute_amr_values(["unknown_method"]) is None


def test_compute_amr_values_mixed_known_unknown():
    """Test compute_amr_values with mixed known and unknown methods."""
    result = compute_amr_values(["password", "unknown_method", "otp"])
    assert set(result) == {"pwd", "otp", "mfa"}


def test_compute_amr_values_deduplication():
    """Test that AMR values are deduplicated (email and sms both give mca)."""
    result = compute_amr_values(["email", "sms"])
    assert result.count("mca") == 1
    assert set(result) == {"mca", "sms", "mfa"}
