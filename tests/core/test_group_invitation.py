import datetime

from canaille.core.endpoints.account import GroupInvitationPayload


def test_group_invitation_payload(app):
    """Test GroupInvitationPayload expiration, encoding and hash generation."""
    with app.app_context():
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id="test-group-id",
            invited_user_id="test-user-id",
        )

        assert payload.expiration_date == expiration_date
        assert not payload.has_expired()

        past_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            hours=1
        )
        expired_payload = GroupInvitationPayload(
            expiration_date_isoformat=past_date.isoformat(),
            group_id="test-group-id",
            invited_user_id="test-user-id",
        )
        assert expired_payload.has_expired()

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
    """Test sending group invitation email and displaying invitation URL."""
    res = testclient.get(f"/groups/{bar_group.id}/invite", status=200)

    res.form["email"] = user.emails[0]
    res = res.form.submit(status=200)

    assert len(smtpd.messages) == 1
    email = smtpd.messages[0]
    assert user.emails[0] in email.get("To")
    assert "Invitation to join" in email.get("Subject")
    assert bar_group.display_name in email.get("Subject")

    assert "Invitation sent" in res.text
    invitation_url = res.pyquery(".copy-text")[0].value
    assert "/groups/join/" in invitation_url


def test_group_invitation_nonexistent_user(testclient, logged_admin, foo_group):
    """Test invitation with email not belonging to any user shows error message."""
    res = testclient.get(f"/groups/{foo_group.id}/invite", status=200)

    res.form["email"] = "nonexistent@domain.test"
    res = res.form.submit(status=200)

    assert "No user found with this email address" in res.text


def test_join_group_with_valid_invitation(
    testclient, logged_user, bar_group, backend, app
):
    """Test joining a group with valid invitation adds user to members."""
    with app.app_context():
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=bar_group.id,
            invited_user_id=logged_user.id,
        )

        assert logged_user not in bar_group.members

        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        res = testclient.get(invitation_url, status=302)

        assert "/settings" in res.location

        assert (
            "success",
            f"You have successfully joined {bar_group.display_name}!",
        ) in res.flashes

        res = res.follow()

        backend.reload(bar_group)
        backend.reload(logged_user)
        assert logged_user in bar_group.members


def test_join_group_expired_invitation(testclient, logged_user, bar_group, app):
    """Test joining with expired invitation redirects without crashing."""
    with app.app_context():
        past_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            hours=1
        )
        payload = GroupInvitationPayload(
            expiration_date_isoformat=past_date.isoformat(),
            group_id=bar_group.id,
            invited_user_id=logged_user.id,
        )

        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        testclient.get(invitation_url, status=302)


def test_join_group_invalid_hash(testclient, logged_user, bar_group, app):
    """Test joining with invalid hash redirects without crashing."""
    with app.app_context():
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=bar_group.id,
            invited_user_id=logged_user.id,
        )

        invitation_url = f"/groups/join/{payload.b64()}/invalid-hash"
        testclient.get(invitation_url, status=302)


def test_join_group_invalid_data(testclient, logged_user):
    """Test joining with invalid base64 data redirects without crashing."""
    invitation_url = "/groups/join/invalid-data/some-hash"
    testclient.get(invitation_url, status=302)


def test_join_nonexistent_group(testclient, logged_user, app):
    """Test joining a group that doesn't exist redirects without crashing."""
    with app.app_context():
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id="nonexistent-group-id",
            invited_user_id=logged_user.id,
        )

        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        testclient.get(invitation_url, status=302)


def test_join_group_requires_login(testclient, bar_group, user, app):
    """Test that joining a group requires authentication and redirects to login."""
    with app.app_context():
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=bar_group.id,
            invited_user_id=user.id,
        )

        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        res = testclient.get(invitation_url, status=302)

        assert f"/login/{user.user_name}" in res.location
        assert "next=" not in res.location

        res = res.follow()
        res = res.follow()
        assert "You have been invited to join the group" in res.text
        assert bar_group.display_name in res.text


def test_join_group_invalid_user_redirect(testclient, bar_group, app):
    """Test joining with invalid user ID redirects to account index."""
    with app.app_context():
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=bar_group.id,
            invited_user_id="nonexistent-user-id",
        )

        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        res = testclient.get(invitation_url, status=302)

        assert res.location.endswith("/")


def test_invitation_button_visible_on_group_page(testclient, logged_admin, foo_group):
    """Test that invite button is visible on group management page."""
    res = testclient.get(f"/groups/{foo_group.display_name}", status=200)
    assert "Invite Members" in res.text
    assert f"/groups/{foo_group.display_name}/invite" in res.text


def test_group_invitation_duplicate_member_detection(
    testclient, logged_admin, foo_group, user, backend
):
    """Test that inviting existing members shows error message."""
    res = testclient.get(f"/groups/{foo_group.display_name}/invite", status=200)

    res.form["email"] = user.emails[0]
    res = res.form.submit(status=200)

    assert "already a member" in res.text


def test_join_group_wrong_email_invitation(
    testclient, logged_user, bar_group, admin, app
):
    """Test joining with invitation sent to different user shows error."""
    with app.app_context():
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=bar_group.id,
            invited_user_id=admin.id,
        )

        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        res = testclient.get(invitation_url, status=302)

        assert (
            "error",
            "This invitation was not sent to you.",
        ) in res.flashes


def test_join_group_already_member_handling(
    testclient, logged_user, foo_group, backend, app
):
    """Test joining a group when already a member shows appropriate message."""
    with app.app_context():
        expiration_date = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(hours=24)
        payload = GroupInvitationPayload(
            expiration_date_isoformat=expiration_date.isoformat(),
            group_id=foo_group.id,
            invited_user_id=logged_user.id,
        )

        invitation_url = f"/groups/join/{payload.b64()}/{payload.build_hash()}"
        res = testclient.get(invitation_url, status=302)

        res = res.follow()
        assert "already a member" in res.text


def test_group_invitation_no_smtp_requirement(testclient, logged_admin, foo_group):
    """Test that invitation form requires SMTP configuration and fails without it."""
    testclient.app.config["CANAILLE"]["SMTP"] = None

    testclient.get(f"/groups/{foo_group.id}/invite", status=500, expect_errors=True)


def test_group_invitation_workflow_with_email_extraction(
    testclient, logged_admin, bar_group, user, smtpd, backend
):
    """Test complete invitation workflow: email sending, URL generation and validation."""
    res = testclient.get(f"/groups/{bar_group.display_name}/invite", status=200)
    res.form["email"] = user.emails[0]
    res = res.form.submit(status=200)

    assert len(smtpd.messages) == 1

    invitation_url = res.pyquery(".copy-text")[0].value
    assert "/groups/join/" in invitation_url

    from urllib.parse import urlparse

    parsed_url = urlparse(invitation_url)
    assert parsed_url.path.startswith("/groups/join/")

    path_parts = parsed_url.path.split("/")
    assert len(path_parts) == 5
    assert path_parts[1] == "groups"
    assert path_parts[2] == "join"
    assert len(path_parts[3]) > 0
    assert len(path_parts[4]) > 0


def test_invite_to_group_unauthorized_user(testclient, logged_user, bar_group):
    """Test that a user without access to a group cannot invite others to it."""
    testclient.get(f"/groups/{bar_group.display_name}/invite", status=403)
