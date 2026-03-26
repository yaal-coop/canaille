def test_login_page(build_mode, database_mode, client):
    response = client.get("/login")
    assert response.status_code == 200, response.text


def test_about_page(build_mode, database_mode, client):
    response = client.get("/about")
    assert response.status_code == 200, response.text


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
