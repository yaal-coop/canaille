"""Tests the behavior of Canaille depending on the OIDC 'prompt' parameter.

https://openid.net/specs/openid-connect-core-1_0.html#AuthorizationEndpoint
"""

import datetime
import uuid
from urllib.parse import parse_qs
from urllib.parse import urlsplit

from flask import url_for

from canaille.app import models
from canaille.core.endpoints.account import RegistrationPayload


def test_prompt_none(testclient, logged_user, client, backend):
    """Nominal case with prompt=none."""
    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=logged_user,
        scope=["openid", "profile"],
    )
    backend.save(consent)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="none",
            redirect_uri="https://client.test/redirect1",
        ),
        status=302,
    )
    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    assert "code" in params

    backend.delete(consent)


def test_prompt_not_logged(testclient, user, client, backend):
    """Prompt=none should return a login_required error when no user is logged in.

    login_required     The Authorization Server requires End-User
    authentication.     This error MAY be returned when the prompt
    parameter value in the     Authentication Request is none, but the
    Authentication Request     cannot be completed without displaying a
    user interface for End-User     authentication.
    """
    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=user,
        scope=["openid", "profile"],
    )
    backend.save(consent)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="none",
            redirect_uri="https://client.test/redirect1",
        ),
        status=302,
    )
    params = parse_qs(urlsplit(res.location).query)
    assert params["error"] == ["login_required"]
    backend.delete(consent)


def test_prompt_no_consent(testclient, logged_user, client):
    """Prompt=none should return a consent_required error when user are logged in but have not granted their consent.

    consent_required The Authorization Server requires End-User consent.
    This error MAY be returned when the prompt parameter value in the
    Authentication Request is none, but the Authentication Request
    cannot be completed without displaying a user interface for End-User
    consent.
    """
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="none",
            redirect_uri="https://client.test/redirect1",
        ),
        status=302,
    )
    params = parse_qs(urlsplit(res.location).query)
    assert params["error"] == ["consent_required"]


def test_prompt_create_logged(testclient, logged_user, client, backend):
    """If prompt=create and user is already logged in, then go straight to the consent page."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True

    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=logged_user,
        scope=["openid", "profile"],
    )
    backend.save(consent)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="create",
            redirect_uri="https://client.test/redirect1",
        ),
        status=302,
    )
    assert res.location.startswith(client.redirect_uris[0])

    backend.delete(consent)


def test_prompt_create_registration_disabled(testclient, trusted_client, smtpd):
    """If prompt=create but Canaille registration is disabled, an error response should be returned.

    If the OpenID Provider receives a prompt value that it does not
    support (not declared in the prompt_values_supported metadata field)
    the OP SHOULD respond with an HTTP 400 (Bad Request) status code and
    an error value of invalid_request. It is RECOMMENDED that the OP
    return an error_description value identifying the invalid parameter
    value.
    """
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=trusted_client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="create",
            redirect_uri="https://myotherdomain.test/redirect1",
        ),
        status=302,
    )

    params = parse_qs(urlsplit(res.location).query)
    assert params["error"] == ["invalid_request"]
    assert params["error_description"] == ["prompt 'create' value is not supported"]


def test_prompt_create_not_logged(testclient, trusted_client, smtpd):
    """If prompt=create and user is not logged in, then display the registration form.

    Check that the user is correctly redirected to the client page after
    the registration process.
    """
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=trusted_client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="create",
            redirect_uri=trusted_client.redirect_uris[0],
        ),
    )

    # Display the registration form
    res = res.follow()
    res.form["email"] = "foo@bar.test"
    res = res.form.submit()

    # Checks the registration mail is sent
    assert len(smtpd.messages) == 1

    # Simulate a click on the validation link in the mail
    payload = RegistrationPayload(
        creation_date_isoformat=datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        user_name="",
        user_name_editable=True,
        email="foo@bar.test",
        groups=[],
    )
    registration_url = url_for(
        "core.account.registration",
        data=payload.b64(),
        hash=payload.build_hash(),
        _external=True,
    )

    # Fill the user creation form
    res = testclient.get(registration_url)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "i'm a little pea"
    res.form["password2"] = "i'm a little pea"
    res.form["family_name"] = "newuser"
    res = res.form.submit()

    assert res.flashes == [
        ("success", "Your account has been created successfully."),
    ]

    # Return to the client
    res = res.follow()
    assert res.location.startswith(trusted_client.redirect_uris[0])


def test_prompt_login_logged(testclient, logged_user, client, backend):
    """If prompt=login and user is already logged in, then the user should be logged in again.

    The Authorization Server SHOULD prompt the End-User for reauthentication.
    If it cannot reauthenticate the End-User, it MUST return an error,
    typically login_required.
    """
    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=logged_user,
        scope=["openid", "profile"],
    )
    backend.save(consent)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="login",
            redirect_uri="https://client.test/redirect1",
        ),
        status=302,
    )
    res = res.follow()

    assert res.template == "core/password.html"
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302).follow()

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    assert "code" in params

    backend.delete(consent)


def test_prompt_consent(testclient, logged_user, client, backend):
    """If prompt=consent and users already have given their consent, then they should give it again.

    The Authorization Server SHOULD prompt the End-User for consent
    before returning information to the Client. If it cannot obtain
    consent, it MUST return an error, typically consent_required.
    """
    original_consent_date = datetime.datetime.now(
        datetime.timezone.utc
    ) - datetime.timedelta(minutes=1)
    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=logged_user,
        scope=["openid", "profile"],
        issue_date=original_consent_date,
    )
    backend.save(consent)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="consent",
            redirect_uri="https://client.test/redirect1",
        ),
    )

    assert res.template == "oidc/authorize.html"
    res = res.form.submit(name="answer", value="accept")

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    assert "code" in params

    backend.reload(consent)
    assert consent.issue_date > original_consent_date

    backend.delete(consent)
