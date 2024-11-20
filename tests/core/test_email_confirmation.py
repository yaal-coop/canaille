import datetime
from unittest import mock

import time_machine
from flask import url_for

from canaille.core.endpoints.account import EmailConfirmationPayload
from canaille.core.endpoints.account import RegistrationPayload


def test_confirmation_disabled_email_editable(testclient, backend, logged_user):
    """If email confirmation is disabled, users should be able to pick any
    email."""
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    res = testclient.get("/profile/user")
    assert "readonly" not in res.form["emails-0"].attrs
    assert not any(field.id == "add_email" for field in res.form.fields["action"])

    res = res.form.submit(name="fieldlist_add", value="emails-0")
    res.form["emails-0"] = "email1@mydomain.test"
    res.form["emails-1"] = "email2@mydomain.test"

    res = res.form.submit(name="action", value="edit-profile")
    assert res.flashes == [("success", "Profile updated successfully.")]
    res = res.follow()

    backend.reload(logged_user)

    assert logged_user.emails == ["email1@mydomain.test", "email2@mydomain.test"]


def test_confirmation_unset_smtp_disabled_email_editable(
    testclient, backend, logged_admin, user
):
    """If email confirmation is unset and no SMTP server has been configured,
    then email confirmation cannot be enabled, thus users must be able to pick
    any email."""
    testclient.app.config["CANAILLE"]["SMTP"] = None
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = None

    res = testclient.get("/profile/user")
    assert "readonly" not in res.form["emails-0"].attrs
    assert not any(field.id == "add_email" for field in res.form.fields["action"])

    res = res.form.submit(name="fieldlist_add", value="emails-0")
    res.form["emails-0"] = "email1@mydomain.test"
    res.form["emails-1"] = "email2@mydomain.test"

    res = res.form.submit(name="action", value="edit-profile")
    assert res.flashes == [("success", "Profile updated successfully.")]
    res = res.follow()

    backend.reload(user)
    assert user.emails == ["email1@mydomain.test", "email2@mydomain.test"]


def test_confirmation_enabled_smtp_disabled_readonly(testclient, backend, logged_user):
    """If email confirmation is enabled and no SMTP server is configured, this
    might be a misconfiguration, or a temporary SMTP disabling.

    In doubt, users cannot edit their emails.
    """
    testclient.app.config["CANAILLE"]["SMTP"] = None
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = True

    res = testclient.get("/profile/user")
    assert "readonly" in res.forms["emailconfirmationform"]["old_emails-0"].attrs
    assert "emails-0" not in res.forms["baseform"].fields

    res.forms["emailconfirmationform"]["old_emails-0"] = "email1@mydomain.test"
    assert "action" not in res.forms["emailconfirmationform"].fields


def test_confirmation_unset_smtp_enabled_email_admin_editable(
    testclient, backend, logged_admin, user
):
    """Administrators should be able to edit user email addresses, even when
    email confirmation is unset and SMTP is configured."""
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = None

    res = testclient.get("/profile/user")
    assert "readonly" not in res.form["emails-0"].attrs
    assert not any(field.id == "add_email" for field in res.form.fields["action"])

    res = res.form.submit(name="fieldlist_add", value="emails-0")
    res.form["emails-0"] = "email1@mydomain.test"
    res.form["emails-1"] = "email2@mydomain.test"

    res = res.form.submit(name="action", value="edit-profile")
    assert res.flashes == [("success", "Profile updated successfully.")]
    res = res.follow()

    backend.reload(user)
    assert user.emails == ["email1@mydomain.test", "email2@mydomain.test"]


def test_confirmation_enabled_smtp_disabled_admin_editable(
    testclient, backend, logged_admin, user
):
    """Administrators should be able to edit user email addresses, even when
    email confirmation is enabled and SMTP is disabled."""
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = True
    testclient.app.config["CANAILLE"]["SMTP"] = None

    res = testclient.get("/profile/user")
    assert "readonly" not in res.form["emails-0"].attrs
    assert not any(field.id == "add_email" for field in res.form.fields["action"])

    res = res.form.submit(name="fieldlist_add", value="emails-0")
    res.form["emails-0"] = "email1@mydomain.test"
    res.form["emails-1"] = "email2@mydomain.test"

    res = res.form.submit(name="action", value="edit-profile")
    assert res.flashes == [("success", "Profile updated successfully.")]
    res = res.follow()

    backend.reload(user)
    assert user.emails == ["email1@mydomain.test", "email2@mydomain.test"]


def test_confirmation_unset_smtp_enabled_email_user_validation(
    smtpd, testclient, backend, user
):
    """If email confirmation is unset and there is a SMTP server configured,
    then users emails should be validated by sending a confirmation email."""
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = None

    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get("/login")
        res.form["login"] = "user"
        res = res.form.submit().follow()
        res.form["password"] = "correct horse battery staple"
        res = res.form.submit()

    with time_machine.travel("2020-01-01 02:00:00+00:00", tick=False):
        res = testclient.get("/profile/user")

    assert "readonly" in res.forms["emailconfirmationform"]["old_emails-0"].attrs

    with time_machine.travel("2020-01-01 02:00:00+00:00", tick=False):
        res.forms["emailconfirmationform"]["new_email"] = "new_email@mydomain.test"
        res = res.forms["emailconfirmationform"].submit(
            name="action", value="add_email"
        )

    assert res.flashes == [
        (
            "success",
            "An email has been sent to the email address. "
            "Please check your inbox and click on the verification link it contains",
        )
    ]

    email_confirmation = EmailConfirmationPayload(
        "2020-01-01T02:00:00+00:00",
        "user",
        "new_email@mydomain.test",
    )
    email_confirmation_url = url_for(
        "core.account.email_confirmation",
        data=email_confirmation.b64(),
        hash=email_confirmation.build_hash(),
        _external=True,
    )

    assert len(smtpd.messages) == 1
    email_content = (
        str(smtpd.messages[0].get_payload()[0]).replace("=\n", "").replace("=3D", "=")
    )
    assert email_confirmation_url in email_content

    with time_machine.travel("2020-01-01 03:00:00+00:00", tick=False):
        res = testclient.get(email_confirmation_url)

    assert ("success", "Your email address have been confirmed.") in res.flashes
    backend.reload(user)
    assert "new_email@mydomain.test" in user.emails


def test_confirmation_invalid_link(testclient, backend, user):
    """Random confirmation links should fail."""
    res = testclient.get("/email-confirmation/invalid/invalid")
    assert (
        "error",
        "The email confirmation link that brought you here is invalid.",
    ) in res.flashes


def test_confirmation_mail_form_failed(testclient, backend, user):
    """Tests when an error happens during the mail sending."""
    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get("/login")
        res.form["login"] = "user"
        res = res.form.submit().follow()
        res.form["password"] = "correct horse battery staple"
        res = res.form.submit()

    with time_machine.travel("2020-01-01 02:00:00+00:00", tick=False):
        res = testclient.get("/profile/user")

    assert "readonly" in res.forms["emailconfirmationform"]["old_emails-0"].attrs

    with time_machine.travel("2020-01-01 02:00:00+00:00", tick=False):
        res.forms["emailconfirmationform"]["new_email"] = "invalid"
        res = res.forms["emailconfirmationform"].submit(
            name="action", value="add_email"
        )

    assert res.flashes == [("error", "Email addition failed.")]
    backend.reload(user)
    assert user.emails == ["john@doe.test"]


@mock.patch("smtplib.SMTP")
def test_confirmation_mail_send_failed(SMTP, smtpd, testclient, backend, user):
    """Tests when an error happens during the mail sending."""
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get("/login")
        res.form["login"] = "user"
        res = res.form.submit().follow()
        res.form["password"] = "correct horse battery staple"
        res = res.form.submit()

    with time_machine.travel("2020-01-01 02:00:00+00:00", tick=False):
        res = testclient.get("/profile/user")

    assert "readonly" in res.forms["emailconfirmationform"]["old_emails-0"].attrs

    with time_machine.travel("2020-01-01 02:00:00+00:00", tick=False):
        res.forms["emailconfirmationform"]["new_email"] = "new_email@mydomain.test"
        res = res.forms["emailconfirmationform"].submit(
            name="action", value="add_email", expect_errors=True
        )

    assert res.flashes == [("error", "Could not send the verification email")]
    backend.reload(user)
    assert user.emails == ["john@doe.test"]


def test_confirmation_expired_link(testclient, backend, user):
    """Expired valid confirmation links should fail."""
    email_confirmation = EmailConfirmationPayload(
        "2020-01-01T01:00:00+00:00",
        "user",
        "new_email@mydomain.test",
    )
    email_confirmation_url = url_for(
        "core.account.email_confirmation",
        data=email_confirmation.b64(),
        hash=email_confirmation.build_hash(),
        _external=True,
    )

    with time_machine.travel("2021-01-01 01:00:00+00:00", tick=False):
        res = testclient.get(email_confirmation_url)

    assert (
        "error",
        "The email confirmation link that brought you here has expired.",
    ) in res.flashes
    backend.reload(user)
    assert "new_email@mydomain.test" not in user.emails


def test_confirmation_invalid_hash_link(testclient, backend, user):
    """Confirmation link with invalid hashes should fail."""
    email_confirmation = EmailConfirmationPayload(
        "2020-01-01T01:00:00+00:00",
        "user",
        "new_email@mydomain.test",
    )
    email_confirmation_url = url_for(
        "core.account.email_confirmation",
        data=email_confirmation.b64(),
        hash="invalid",
        _external=True,
    )

    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get(email_confirmation_url)

    assert (
        "error",
        "The invitation link that brought you here was invalid.",
    ) in res.flashes
    backend.reload(user)
    assert "new_email@mydomain.test" not in user.emails


def test_confirmation_invalid_user_link(testclient, backend, user):
    """Confirmation link about an unexisting user should fail.

    For instance, when the user account has been deleted between the
    mail is sent and the link is clicked.
    """
    email_confirmation = EmailConfirmationPayload(
        "2020-01-01T01:00:00+00:00",
        "invalid-user",
        "new_email@mydomain.test",
    )
    email_confirmation_url = url_for(
        "core.account.email_confirmation",
        data=email_confirmation.b64(),
        hash=email_confirmation.build_hash(),
        _external=True,
    )

    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get(email_confirmation_url)

    assert (
        "error",
        "The email confirmation link that brought you here is invalid.",
    ) in res.flashes
    backend.reload(user)
    assert "new_email@mydomain.test" not in user.emails


def test_confirmation_email_already_confirmed_link(testclient, backend, user, admin):
    """Clicking twice on a confirmation link should fail."""
    email_confirmation = EmailConfirmationPayload(
        "2020-01-01T01:00:00+00:00",
        "user",
        "john@doe.test",
    )
    email_confirmation_url = url_for(
        "core.account.email_confirmation",
        data=email_confirmation.b64(),
        hash=email_confirmation.build_hash(),
        _external=True,
    )

    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get(email_confirmation_url)

    assert (
        "error",
        "This address email have already been confirmed.",
    ) in res.flashes
    backend.reload(user)
    assert "new_email@mydomain.test" not in user.emails


def test_confirmation_email_already_used_link(testclient, backend, user, admin):
    """Confirmation link should fail if the target email is already associated
    to another account.

    For instance, if an administrator already put this email to someone
    else's profile.
    """
    email_confirmation = EmailConfirmationPayload(
        "2020-01-01T01:00:00+00:00",
        "user",
        "jane@doe.test",
    )
    email_confirmation_url = url_for(
        "core.account.email_confirmation",
        data=email_confirmation.b64(),
        hash=email_confirmation.build_hash(),
        _external=True,
    )

    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get(email_confirmation_url)

    assert (
        "error",
        "This address email is already associated with another account.",
    ) in res.flashes
    backend.reload(user)
    assert "new_email@mydomain.test" not in user.emails


def test_delete_email(testclient, logged_user, backend):
    """Tests that user can deletes its emails unless they have only one
    left."""
    res = testclient.get("/profile/user")
    assert "email_remove" not in res.forms["emailconfirmationform"].fields

    logged_user.emails = logged_user.emails + ["new@email.test"]
    backend.save(logged_user)
    res = testclient.get("/profile/user")
    assert "email_remove" in res.forms["emailconfirmationform"].fields

    res = res.forms["emailconfirmationform"].submit(
        name="email_remove", value="new@email.test"
    )
    assert res.flashes == [("success", "The email have been successfully deleted.")]

    backend.reload(logged_user)
    assert logged_user.emails == ["john@doe.test"]


def test_delete_wrong_email(testclient, logged_user, backend):
    """Tests that removing an already removed email do not produce anything."""
    logged_user.emails = logged_user.emails + ["new@email.test"]
    backend.save(logged_user)

    res = testclient.get("/profile/user")

    res1 = res.forms["emailconfirmationform"].submit(
        name="email_remove", value="new@email.test"
    )
    assert res1.flashes == [("success", "The email have been successfully deleted.")]

    res2 = res.forms["emailconfirmationform"].submit(
        name="email_remove", value="new@email.test"
    )
    assert res2.flashes == [("error", "Email deletion failed.")]

    backend.reload(logged_user)
    assert logged_user.emails == ["john@doe.test"]


def test_delete_last_email(testclient, logged_user, backend):
    """Tests that users cannot remove their last email address."""
    logged_user.emails = logged_user.emails + ["new@email.test"]
    backend.save(logged_user)

    res = testclient.get("/profile/user")

    res1 = res.forms["emailconfirmationform"].submit(
        name="email_remove", value="new@email.test"
    )
    assert res1.flashes == [("success", "The email have been successfully deleted.")]

    res2 = res.forms["emailconfirmationform"].submit(
        name="email_remove", value="john@doe.test"
    )
    assert res2.flashes == [("error", "Email deletion failed.")]

    backend.reload(logged_user)
    assert logged_user.emails == ["john@doe.test"]


def test_edition_forced_mail(testclient, logged_user, backend):
    """Tests that users that must perform email verification cannot force the
    profile form."""
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    testclient.post(
        "/profile/user",
        {
            "csrf_token": form["csrf_token"].value,
            "emails-0": "new@email.test",
            "action": "edit-profile",
        },
    )

    backend.reload(logged_user)
    assert logged_user.emails == ["john@doe.test"]


def test_invitation_form_mail_field_readonly(testclient):
    """Tests that the email field is readonly in the invitation form creation
    if email confirmation is enabled."""
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = True

    payload = RegistrationPayload(
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "someoneelse",
        False,
        "someone@mydomain.test",
        [],
    )
    hash = payload.build_hash()
    b64 = payload.b64()

    res = testclient.get(f"/register/{b64}/{hash}")
    assert "readonly" in res.form["emails-0"].attrs


def test_invitation_form_mail_field_writable(testclient):
    """Tests that the email field is writable in the invitation form creation
    if email confirmation is disabled."""
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    payload = RegistrationPayload(
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "someoneelse",
        False,
        "someone@mydomain.test",
        [],
    )
    hash = payload.build_hash()
    b64 = payload.b64()

    res = testclient.get(f"/register/{b64}/{hash}")
    assert "readonly" not in res.form["emails-0"].attrs
