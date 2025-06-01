from urllib.parse import parse_qs
from urllib.parse import urlsplit

from joserfc import jwt

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


def test_request_object_uri_query(
    testclient, logged_user, trusted_client, client_jwk, httpserver
):
    """Test an authentication request that uses the request_uri parameter."""
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
