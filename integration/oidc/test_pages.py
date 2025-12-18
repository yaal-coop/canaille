import pytest


@pytest.mark.requires_extra("oidc")
def test_well_known_openid_configuration(build_mode, database_mode, client):
    response = client.get("/.well-known/openid-configuration")
    assert response.status_code == 200, response.text
    assert "authorization_endpoint" in response.json()


@pytest.mark.requires_extra("oidc")
def test_well_known_oauth_authorization_server(build_mode, database_mode, client):
    response = client.get("/.well-known/oauth-authorization-server")
    assert response.status_code == 200, response.text
    assert "authorization_endpoint" in response.json()


@pytest.mark.requires_extra("oidc")
def test_jwks(build_mode, database_mode, client):
    response = client.get("/oauth/jwks.json")
    assert response.status_code == 200, response.text
    assert "keys" in response.json()


@pytest.mark.requires_extra("oidc")
def test_consents_page(build_mode, database_mode, logged_user_client):
    response = logged_user_client.get("/consent/")
    assert response.status_code == 200, response.text


@pytest.mark.requires_extra("oidc")
def test_clients_page(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/admin/client/")
    assert response.status_code == 200, response.text


@pytest.mark.requires_extra("oidc")
def test_client_creation_page(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/admin/client/add")
    assert response.status_code == 200, response.text


@pytest.mark.requires_extra("oidc")
def test_tokens_page(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/admin/token/")
    assert response.status_code == 200, response.text
