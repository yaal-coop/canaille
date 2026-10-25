import uuid
from urllib.parse import parse_qs
from urllib.parse import urlsplit

import pytest
from joserfc import jwt

from canaille.app import models
from canaille.oidc.utils import MAX_DOCUMENT_SIZE

from . import client_credentials


def test_request_object_query(testclient, logged_user, trusted_client, client_jwk):
    """Test an authentication request that uses the request parameter."""
    payload = dict(
        response_type="code",
        client_id=trusted_client.client_id,
        scope="openid profile email groups address phone",
        nonce="somenonce",
        redirect_uri=trusted_client.redirect_uris[0],
    )
    request_obj = jwt.encode({"alg": "RS256"}, payload, client_jwk)
    res = testclient.get(
        "/oauth/authorize",
        params=dict(client_id=trusted_client.client_id, request=request_obj),
        status=302,
    )

    assert res.location.startswith(trusted_client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile email groups address phone",
            redirect_uri=trusted_client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(trusted_client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    assert access_token


@pytest.mark.parametrize(
    "request_uri",
    [
        "http://127.0.0.1:1/request_obj",
        "file:///etc/passwd",
        # unparsable URIs raise outside of the httpx2 exception hierarchy
        "http://xn--/",
    ],
)
def test_unreachable_request_object_uri(
    testclient, backend, logged_user, trusted_client, request_uri
):
    """Request objects that cannot be downloaded are a client error, not a server error."""
    trusted_client.request_uris = [request_uri]
    backend.save(trusted_client)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(client_id=trusted_client.client_id, request_uri=request_uri),
        status=400,
    )
    res.mustcontain("The request_uri in the authorization request returns an error")


def test_too_big_request_object(
    testclient, backend, logged_user, trusted_client, httpserver
):
    """Request objects are bounded in size, as they are read in memory."""
    request_uri = f"http://{httpserver.host}:{httpserver.port}/request_obj"
    trusted_client.request_uris = [request_uri]
    backend.save(trusted_client)
    httpserver.expect_request("/request_obj").respond_with_data(
        "a" * (MAX_DOCUMENT_SIZE + 1)
    )

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            client_id=trusted_client.client_id,
            request_uri=request_uri,
        ),
        status=400,
    )
    res.mustcontain("The request_uri in the authorization request returns an error")


def test_unregistered_request_object_uri(
    testclient, logged_user, trusted_client, client_jwk, httpserver
):
    """Request objects are not downloaded from URIs the client did not register."""
    request_uri = f"http://{httpserver.host}:{httpserver.port}/request_obj"
    payload = dict(
        response_type="code",
        client_id=trusted_client.client_id,
        scope="openid profile email groups address phone",
        nonce="somenonce",
        redirect_uri=trusted_client.redirect_uris[0],
    )
    request_obj = jwt.encode({"alg": "RS256"}, payload, client_jwk)
    httpserver.expect_request("/request_obj").respond_with_data(request_obj)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(client_id=trusted_client.client_id, request_uri=request_uri),
        status=400,
    )
    res.mustcontain("The request_uri in the authorization request returns an error")
    assert not httpserver.log


def test_request_object_uri_query(
    testclient, backend, logged_user, trusted_client, client_jwk, httpserver
):
    """Test an authentication request that uses the request_uri parameter."""
    request_uri = f"http://{httpserver.host}:{httpserver.port}/request_obj"
    trusted_client.request_uris = [request_uri]
    backend.save(trusted_client)
    payload = dict(
        response_type="code",
        client_id=trusted_client.client_id,
        scope="openid profile email groups address phone",
        nonce="somenonce",
        redirect_uri=trusted_client.redirect_uris[0],
    )
    request_obj = jwt.encode({"alg": "RS256"}, payload, client_jwk)
    httpserver.expect_request("/request_obj").respond_with_data(request_obj)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(client_id=trusted_client.client_id, request_uri=request_uri),
        status=302,
    )

    assert res.location.startswith(trusted_client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile email groups address phone",
            redirect_uri=trusted_client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(trusted_client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    assert access_token


def test_request_object_scope_is_displayed(
    testclient, logged_user, client, client_jwk, backend
):
    """The consent page displays the scopes of the request object, not the query ones."""
    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=logged_user,
        scope=["openid"],
    )
    backend.save(consent)

    request_obj = jwt.encode(
        {"alg": "RS256"},
        dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid email",
            nonce="somenonce",
            redirect_uri=client.redirect_uris[0],
        ),
        client_jwk,
    )
    res = testclient.get(
        "/oauth/authorize",
        params=dict(client_id=client.client_id, scope="openid", request=request_obj),
        status=200,
    )
    res.mustcontain("Your e-mail address.")

    res = res.form.submit(name="answer", value="accept", status=302)
    backend.reload(consent)
    assert set(consent.scope) == {"openid", "email"}

    backend.delete(consent)


def test_request_object_redirect_uri_on_consent_required(
    testclient, logged_user, client, client_jwk
):
    """The consent_required error goes to the redirect URI of the request object."""
    request_obj = jwt.encode(
        {"alg": "RS256"},
        dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid",
            nonce="somenonce",
            redirect_uri=client.redirect_uris[0],
            prompt="none",
        ),
        client_jwk,
    )
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            client_id=client.client_id,
            redirect_uri="https://attacker.test/callback",
            prompt="none",
            request=request_obj,
        ),
        status=302,
    )
    assert res.location.startswith(client.redirect_uris[0])
    assert parse_qs(urlsplit(res.location).query)["error"] == ["consent_required"]


def test_request_object_prompt(testclient, logged_user, client, client_jwk):
    """The prompt of the request object is applied."""
    request_obj = jwt.encode(
        {"alg": "RS256"},
        dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid",
            nonce="somenonce",
            redirect_uri=client.redirect_uris[0],
            prompt="login",
        ),
        client_jwk,
    )
    res = testclient.get(
        "/oauth/authorize",
        params=dict(client_id=client.client_id, request=request_obj),
        status=302,
    )
    assert "/auth/" in res.location
