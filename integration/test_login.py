from integration.conftest import extract_csrf_token


def test_login_page_loads(client):
    """Verify the login page loads successfully."""
    response = client.get("/login")
    assert response.status_code == 200
    assert "login" in response.text.lower()


def test_login_flow(client, user_data):
    """Test the complete login flow with username and password."""
    # Step 1: Get the login page and extract CSRF token
    response = client.get("/login")
    assert response.status_code == 200
    csrf_token = extract_csrf_token(response.text)

    # Step 2: Submit username
    response = client.post(
        "/login",
        data={"login": "testuser", "csrf_token": csrf_token},
    )
    assert response.status_code == 200
    assert "password" in response.text.lower()
    csrf_token = extract_csrf_token(response.text)

    # Step 3: Submit password
    response = client.post(
        "/auth/password",
        data={"password": "testpassword123", "csrf_token": csrf_token},
    )
    assert response.status_code == 200
    assert "testuser" in response.text.lower() or "Test" in response.text


def test_profile_page_loads_after_login(client, user_data):
    """Verify that the profile page loads after authentication."""
    # Login first
    response = client.get("/login")
    csrf_token = extract_csrf_token(response.text)

    response = client.post(
        "/login",
        data={"login": "testuser", "csrf_token": csrf_token},
    )
    csrf_token = extract_csrf_token(response.text)

    response = client.post(
        "/auth/password",
        data={"password": "testpassword123", "csrf_token": csrf_token},
    )

    # Access the user's own profile page
    response = client.get(f"/profile/{user_data['user_name']}")
    assert response.status_code == 200
    assert "testuser" in response.text.lower() or "Test" in response.text
