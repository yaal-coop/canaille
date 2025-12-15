import httpx
import pytest

from integration.utils import extract_csrf_token


@pytest.fixture
def logged_user_client(canaille_server, user_data):
    """Create an httpx client logged in as regular user."""
    with httpx.Client(base_url=canaille_server, follow_redirects=True) as client:
        response = client.get("/login")
        csrf_token = extract_csrf_token(response.text)

        response = client.post(
            "/login",
            data={"login": user_data["login"], "csrf_token": csrf_token},
        )
        csrf_token = extract_csrf_token(response.text)

        client.post(
            "/auth/password",
            data={"password": "testpassword123", "csrf_token": csrf_token},
        )

        yield client


# Public pages


def test_login_page(build_mode, database_mode, client):
    response = client.get("/login")
    assert response.status_code == 200, response.text


def test_about_page(build_mode, database_mode, client):
    response = client.get("/about")
    assert response.status_code == 200, response.text


def test_oidc_well_known_openid_configuration(build_mode, database_mode, client):
    response = client.get("/.well-known/openid-configuration")
    assert response.status_code == 200, response.text
    assert "authorization_endpoint" in response.json()


def test_oidc_well_known_oauth_authorization_server(build_mode, database_mode, client):
    response = client.get("/.well-known/oauth-authorization-server")
    assert response.status_code == 200, response.text
    assert "authorization_endpoint" in response.json()


def test_oidc_jwks(build_mode, database_mode, client):
    response = client.get("/oauth/jwks.json")
    assert response.status_code == 200, response.text
    assert "keys" in response.json()


# User pages


def test_home_page(build_mode, database_mode, logged_user_client):
    response = logged_user_client.get("/")
    assert response.status_code == 200, response.text


def test_own_profile_page(build_mode, database_mode, logged_user_client, user_data):
    response = logged_user_client.get(f"/profile/{user_data['user_name']}")
    assert response.status_code == 200, response.text
    assert "testuser" in response.text.lower()


def test_own_profile_settings_page(
    build_mode, database_mode, logged_user_client, user_data
):
    response = logged_user_client.get(f"/profile/{user_data['user_name']}/settings")
    assert response.status_code == 200, response.text


def test_consents_page(build_mode, database_mode, logged_user_client):
    response = logged_user_client.get("/consent/")
    assert response.status_code == 200, response.text


# Admin pages


def test_users_page(build_mode, database_mode, logged_admin_client):
    """Test /users page - exercises Babel's numberformat for pagination."""
    response = logged_admin_client.get("/users")
    assert response.status_code == 200, response.text
    assert "admin" in response.text.lower() or "testuser" in response.text.lower()


def test_profile_creation_page(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/profile")
    assert response.status_code == 200, response.text


def test_groups_page(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/groups/")
    assert response.status_code == 200, response.text


def test_group_creation_page(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/groups/add")
    assert response.status_code == 200, response.text


def test_oidc_clients_page(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/admin/client/")
    assert response.status_code == 200, response.text


def test_oidc_client_creation_page(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/admin/client/add")
    assert response.status_code == 200, response.text


def test_oidc_tokens_page(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/admin/token/")
    assert response.status_code == 200, response.text


def test_mail_preview_page(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/admin/mail")
    assert response.status_code == 200, response.text


def test_mail_test_html(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/admin/mail/test.html")
    assert response.status_code == 200, response.text


def test_mail_test_txt(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/admin/mail/test.txt")
    assert response.status_code == 200, response.text


def test_mail_password_init_html(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/admin/mail/password-init.html")
    assert response.status_code == 200, response.text


def test_mail_reset_html(build_mode, database_mode, logged_admin_client):
    response = logged_admin_client.get("/admin/mail/reset.html")
    assert response.status_code == 200, response.text


def test_view_other_user_profile(
    build_mode, database_mode, logged_admin_client, user_data
):
    response = logged_admin_client.get(f"/profile/{user_data['user_name']}")
    assert response.status_code == 200, response.text
    assert "testuser" in response.text.lower()
