import datetime

from canaille.core.endpoints.account import GroupInvitationPayload


def test_group_invitation_payload(app):
    """Test GroupInvitationPayload functionality."""
    with app.app_context():
        # Create a payload
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id="test-group-id",
            invited_user_id="test-user-id",
        )

        # Test properties
        assert payload.expiration_date == expiration_date
        assert not payload.has_expired()

        # Test expired payload
        past_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            hours=1
        )
        expired_payload = GroupInvitationPayload(
            expiration_date_isoformat=past_date.isoformat(),
            group_id="test-group-id",
            invited_user_id="test-user-id",
        )
        assert expired_payload.has_expired()

        # Test encoding/decoding
        b64_data = payload.b64()
        hash_value = payload.build_hash()
        assert isinstance(b64_data, str)
        assert isinstance(hash_value, str)


def test_group_invitation_form_access(testclient, logged_admin, foo_group):
    """Test that group invitation form is accessible."""
    res = testclient.get(f"/groups/{foo_group.id}/invite", status=200)
    assert "Invite members to" in res.text
    assert foo_group.display_name in res.text
    assert 'name="email"' in res.text


def test_group_invitation_send_email(testclient, logged_admin, bar_group, user, smtpd):
    """Test sending group invitation email."""
    res = testclient.get(f"/groups/{bar_group.id}/invite", status=200)

    # Fill and submit the form with a real user's email
    res.form["email"] = user.emails[0]
    res = res.form.submit(status=200)

    # Check that email was sent
    assert len(smtpd.messages) == 1
    email = smtpd.messages[0]
    assert user.emails[0] in email.get("To")
    assert "Invitation to join" in email.get("Subject")
    assert bar_group.display_name in email.get("Subject")

    # Check that invitation URL is displayed
    assert "Invitation sent" in res.text
    invitation_url = res.pyquery(".copy-text")[0].value
    assert "/groups/join/" in invitation_url


def test_group_invitation_nonexistent_user(testclient, logged_admin, foo_group):
    """Test invitation with email not belonging to any user."""
    res = testclient.get(f"/groups/{foo_group.id}/invite", status=200)

    # Submit email that doesn't belong to any user
    res.form["email"] = "nonexistent@domain.test"
    res = res.form.submit(status=200)

    # Should show error message
    assert "No user found with this email address" in res.text


def test_join_group_with_valid_invitation(
    testclient, logged_user, bar_group, backend, app
):
    """Test joining a group with valid invitation."""
    with app.app_context():
        # Create valid invitation payload
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=bar_group.id,
            invited_user_id=logged_user.id,
        )

        # Verify user is not a member initially (bar_group has admin, not user)
        assert logged_user not in bar_group.members

        # Join group via invitation
        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        res = testclient.get(invitation_url, status=302)

        # Should redirect to account settings page
        assert "/settings" in res.location

        assert (
            "success",
            f"You have successfully joined {bar_group.display_name}!",
        ) in res.flashes

        # Follow redirect to settings page
        res = res.follow()

        # Verify user is now a member
        backend.reload(bar_group)
        backend.reload(logged_user)
        assert logged_user in bar_group.members


def test_join_group_expired_invitation(testclient, logged_user, bar_group, app):
    """Test joining with expired invitation."""
    with app.app_context():
        # Create expired invitation payload
        past_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            hours=1
        )
        payload = GroupInvitationPayload(
            expiration_date_isoformat=past_date.isoformat(),
            group_id=bar_group.id,
            invited_user_id=logged_user.id,
        )

        # Try to join with expired invitation - should redirect (not crash)
        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        testclient.get(invitation_url, status=302)


def test_join_group_invalid_hash(testclient, logged_user, bar_group, app):
    """Test joining with invalid hash."""
    with app.app_context():
        # Create valid payload but use wrong hash
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=bar_group.id,
            invited_user_id=logged_user.id,
        )

        # Use valid data but invalid hash - should redirect (not crash)
        invitation_url = f"/groups/join/{payload.b64()}/invalid-hash"
        testclient.get(invitation_url, status=302)


def test_join_group_invalid_data(testclient, logged_user):
    """Test joining with invalid base64 data."""
    # Use invalid base64 data - should redirect (not crash)
    invitation_url = "/groups/join/invalid-data/some-hash"
    testclient.get(invitation_url, status=302)


def test_join_nonexistent_group(testclient, logged_user, app):
    """Test joining a group that doesn't exist."""
    with app.app_context():
        # Create payload for non-existent group
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id="nonexistent-group-id",
            invited_user_id=logged_user.id,
        )

        # Try to join non-existent group - should redirect (not crash)
        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        testclient.get(invitation_url, status=302)


def test_join_group_requires_login(testclient, bar_group, user, app):
    """Test that joining a group requires authentication."""
    with app.app_context():
        # Create valid invitation payload for a real user
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=bar_group.id,
            invited_user_id=user.id,
        )

        # Try to join without being logged in - should redirect to login
        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        res = testclient.get(invitation_url, status=302)

        # Should redirect to login page with username (no next parameter needed)
        assert f"/login/{user.user_name}" in res.location
        assert "next=" not in res.location

        # Follow the redirect chain to the password page where flash message should appear
        res = res.follow()  # First redirect to /login/username
        res = res.follow()  # Second redirect to /auth/password
        assert "You have been invited to join the group" in res.text
        assert bar_group.display_name in res.text


def test_join_group_invalid_user_redirect(testclient, bar_group, app):
    """Test joining with invalid user ID redirects to account index."""
    with app.app_context():
        # Create invitation payload with non-existent user ID
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=bar_group.id,
            invited_user_id="nonexistent-user-id",
        )

        # Try to join without being logged in with invalid user ID
        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        res = testclient.get(invitation_url, status=302)

        # Should redirect to account index (which redirects to /)
        assert res.location.endswith("/")


def test_invitation_button_visible_on_group_page(testclient, logged_admin, foo_group):
    """Test that invite button is visible on group management page."""
    res = testclient.get(f"/groups/{foo_group.display_name}", status=200)
    assert "Invite Members" in res.text
    assert f"/groups/{foo_group.display_name}/invite" in res.text


def test_group_invitation_duplicate_member_detection(
    testclient, logged_admin, foo_group, user, backend
):
    """Test that inviting existing members is detected."""
    # foo_group fixture already contains user as a member by default
    res = testclient.get(f"/groups/{foo_group.display_name}/invite", status=200)

    # Try to invite existing member (user is already in foo_group)
    res.form["email"] = user.emails[0]
    res = res.form.submit(status=200)

    # Should show error message
    assert "already a member" in res.text


def test_join_group_wrong_email_invitation(testclient, logged_user, bar_group, app):
    """Test joining with invitation sent to different email."""
    with app.app_context():
        # Create invitation for different email
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=bar_group.id,
            invited_user_id="different-user-id",
        )

        # Try to join with invitation not sent to user's email
        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        res = testclient.get(invitation_url, status=302)

        # Should redirect to account index and then to profile page
        res = res.follow()
        if res.status_code == 302:  # Another redirect to profile page
            res = res.follow()
        assert "not sent to you" in res.text


def test_join_group_already_member_handling(
    testclient, logged_user, foo_group, backend, app
):
    """Test joining a group when already a member."""
    # foo_group already has logged_user as member by default
    with app.app_context():
        # Create valid invitation payload
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=foo_group.id,
            invited_user_id=logged_user.id,
        )

        # Try to join group again
        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        res = testclient.get(invitation_url, status=302)

        # Should redirect to account settings page
        res = res.follow()
        assert "already a member" in res.text


def test_group_invitation_no_smtp_requirement(testclient, logged_admin, foo_group):
    """Test that invitation form requires SMTP configuration."""
    # Disable SMTP
    testclient.app.config["CANAILLE"]["SMTP"] = None

    # Should return 500 error when SMTP is not configured
    testclient.get(f"/groups/{foo_group.id}/invite", status=500, expect_errors=True)


def test_group_invitation_workflow_with_email_extraction(
    testclient, logged_admin, bar_group, user, smtpd, backend
):
    """Test email sending and invitation URL generation workflow."""
    # Step 1: Admin sends invitation to a user not in the group
    res = testclient.get(f"/groups/{bar_group.display_name}/invite", status=200)
    res.form["email"] = user.emails[0]
    res = res.form.submit(status=200)

    # Verify email was sent
    assert len(smtpd.messages) == 1

    # Extract invitation URL from the response
    invitation_url = res.pyquery(".copy-text")[0].value
    assert "/groups/join/" in invitation_url

    # Verify the URL structure is correct
    from urllib.parse import urlparse

    parsed_url = urlparse(invitation_url)
    assert parsed_url.path.startswith("/groups/join/")

    # Verify the URL has the expected structure (data/hash)
    path_parts = parsed_url.path.split("/")
    assert len(path_parts) == 5  # ['', 'groups', 'join', 'data', 'hash']
    assert path_parts[1] == "groups"
    assert path_parts[2] == "join"
    assert len(path_parts[3]) > 0  # data part exists
    assert len(path_parts[4]) > 0  # hash part exists
