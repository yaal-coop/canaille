import datetime

from canaille.app import models
from canaille.core.account import RegistrationPayload
from flask import g


def test_invitation(testclient, logged_admin, foo_group, smtpd):
    assert models.User.get_from_login("someone") is None

    res = testclient.get("/invite", status=200)

    res.form["user_name"] = "someone"
    res.form["user_name_editable"] = False
    res.form["email"] = "someone@domain.tld"
    res.form["groups"] = [foo_group.id]
    res = res.form.submit(name="action", value="send", status=200)
    assert len(smtpd.messages) == 1

    url = res.pyquery(".copy-text")[0].value

    # logout
    g.user = None
    with testclient.session_transaction() as sess:
        del sess["user_id"]

    testclient.get("/logout")
    res = testclient.get(url, status=200)

    assert res.form["user_name"].value == "someone"
    assert "readonly" in res.form["user_name"].attrs
    assert res.form["emails-0"].value == "someone@domain.tld"
    assert res.form["groups"].value == [foo_group.id]

    res.form["password1"] = "whatever"
    res.form["password2"] = "whatever"
    res.form["given_name"] = "George"
    res.form["family_name"] = "Abitbol"

    res = res.form.submit(status=302)

    assert ("success", "Your account has been created successfully.") in res.flashes
    res = res.follow(status=200)

    user = models.User.get_from_login("someone")
    foo_group.reload()
    assert user.check_password("whatever")[0]
    assert user.groups == [foo_group]

    with testclient.session_transaction() as sess:
        assert "user_id" in sess
        del sess["user_id"]

    res = testclient.get(url, status=302)
    user.delete()


def test_invitation_editable_user_name(testclient, logged_admin, foo_group, smtpd):
    assert models.User.get_from_login("jackyjack") is None
    assert models.User.get_from_login("djorje") is None

    res = testclient.get("/invite", status=200)

    res.form["user_name"] = "jackyjack"
    res.form["user_name_editable"] = True
    res.form["email"] = "jackyjack@domain.tld"
    res.form["groups"] = [foo_group.id]
    res = res.form.submit(name="action", value="send", status=200)
    assert len(smtpd.messages) == 1

    url = res.pyquery(".copy-text")[0].value

    # logout
    g.user = None
    with testclient.session_transaction() as sess:
        del sess["user_id"]

    res = testclient.get(url, status=200)

    assert res.form["user_name"].value == "jackyjack"
    assert "readonly" not in res.form["user_name"].attrs
    assert res.form["emails-0"].value == "jackyjack@domain.tld"
    assert res.form["groups"].value == [foo_group.id]

    res.form["user_name"] = "djorje"
    res.form["password1"] = "whatever"
    res.form["password2"] = "whatever"
    res.form["given_name"] = "George"
    res.form["family_name"] = "Abitbol"

    res = res.form.submit(status=302)

    assert ("success", "Your account has been created successfully.") in res.flashes
    res = res.follow(status=200)

    user = models.User.get_from_login("djorje")
    foo_group.reload()
    assert user.check_password("whatever")[0]
    assert user.groups == [foo_group]

    with testclient.session_transaction() as sess:
        assert "user_id" in sess
        del sess["user_id"]
    user.delete()


def test_generate_link(testclient, logged_admin, foo_group, smtpd):
    assert models.User.get_from_login("sometwo") is None

    res = testclient.get("/invite", status=200)

    res.form["user_name"] = "sometwo"
    res.form["email"] = "sometwo@domain.tld"
    res.form["groups"] = [foo_group.id]
    res = res.form.submit(name="action", value="generate", status=200)
    assert len(smtpd.messages) == 0

    url = res.pyquery(".copy-text")[0].value

    # logout
    g.user = None
    with testclient.session_transaction() as sess:
        del sess["user_id"]

    res = testclient.get(url, status=200)

    assert res.form["user_name"].value == "sometwo"
    assert res.form["emails-0"].value == "sometwo@domain.tld"
    assert res.form["groups"].value == [foo_group.id]

    res.form["password1"] = "whatever"
    res.form["password2"] = "whatever"
    res.form["given_name"] = "George"
    res.form["family_name"] = "Abitbol"

    res = res.form.submit(status=302)
    res = res.follow(status=200)

    user = models.User.get_from_login("sometwo")
    foo_group.reload()
    assert user.check_password("whatever")[0]
    assert user.groups == [foo_group]

    with testclient.session_transaction() as sess:
        assert "user_id" in sess
        del sess["user_id"]

    res = testclient.get(url, status=302)
    user.delete()


def test_invitation_login_already_taken(testclient, logged_admin):
    res = testclient.get("/invite", status=200)

    res.form["user_name"] = logged_admin.user_name
    res.form["email"] = logged_admin.preferred_email
    res = res.form.submit(name="action", value="send", status=200)

    res.mustcontain("The login &#39;admin&#39; already exists")
    res.mustcontain("The email &#39;jane@doe.com&#39; is already used")


def test_registration(testclient, foo_group):
    payload = RegistrationPayload(
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "someoneelse",
        False,
        "someone@mydomain.tld",
        [foo_group.id],
    )
    b64 = payload.b64()
    hash = payload.build_hash()

    testclient.get(f"/register/{b64}/{hash}", status=200)


def test_registration_formcontrol(testclient):
    payload = RegistrationPayload(
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "someoneelse",
        False,
        "someone@mydomain.tld",
        [],
    )
    b64 = payload.b64()
    hash = payload.build_hash()

    res = testclient.get(f"/register/{b64}/{hash}", status=200)
    assert "emails-1" not in res.form.fields

    res = res.form.submit(status=200, name="fieldlist_add", value="phone_numbers-0")
    assert "phone_numbers-1" in res.form.fields


def test_registration_invalid_hash(testclient, foo_group):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = RegistrationPayload(
        now, "anything", False, "someone@mydomain.tld", [foo_group.id]
    )
    b64 = payload.b64()

    testclient.get(f"/register/{b64}/invalid", status=302)


def test_registration_invalid_data(testclient, foo_group):
    payload = RegistrationPayload(
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "someoneelse",
        False,
        "someone@mydomain.tld",
        [foo_group.id],
    )
    hash = payload.build_hash()

    testclient.get(f"/register/invalid/{hash}", status=302)


def test_registration_more_than_48_hours_after_invitation(testclient, foo_group):
    two_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=48
    )
    payload = RegistrationPayload(
        two_days_ago.isoformat(),
        "someoneelse",
        False,
        "someone@mydomain.tld",
        [foo_group.id],
    )
    hash = payload.build_hash()
    b64 = payload.b64()

    testclient.get(f"/register/{b64}/{hash}", status=302)


def test_registration_no_password(testclient, foo_group):
    payload = RegistrationPayload(
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "someoneelse",
        False,
        "someone@mydomain.tld",
        [foo_group.id],
    )
    hash = payload.build_hash()
    b64 = payload.b64()
    url = f"/register/{b64}/{hash}"

    res = testclient.get(url, status=200)
    assert "required" in res.form["password1"].attrs
    assert "required" in res.form["password2"].attrs

    res = res.form.submit(status=200)
    res.mustcontain("This field is required.")

    assert not models.User.get_from_login("someoneelse")

    with testclient.session_transaction() as sess:
        assert "user_id" not in sess


def test_no_registration_if_logged_in(testclient, logged_user, foo_group):
    payload = RegistrationPayload(
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "someoneelse",
        False,
        "someone@mydomain.tld",
        [foo_group.id],
    )
    hash = payload.build_hash()
    b64 = payload.b64()
    url = f"/register/{b64}/{hash}"

    testclient.get(url, status=302)


def test_unavailable_if_no_smtp(testclient, logged_admin):
    res = testclient.get("/users")
    res.mustcontain("Invite")
    res = testclient.get("/profile")
    res.mustcontain("Invite")
    testclient.get("/invite")

    del testclient.app.config["SMTP"]

    res = testclient.get("/users")
    res.mustcontain(no="Invite")
    res = testclient.get("/profile")
    res.mustcontain(no="Invite")
    testclient.get("/invite", status=500, expect_errors=True)


def test_groups_are_saved_even_when_user_does_not_have_read_permission(
    testclient, foo_group
):
    testclient.app.config["ACL"]["DEFAULT"]["READ"] = [
        "user_name"
    ]  # remove groups from default read permissions

    payload = RegistrationPayload(
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "someoneelse",
        False,
        "someone@mydomain.tld",
        [foo_group.id],
    )
    b64 = payload.b64()
    hash = payload.build_hash()

    res = testclient.get(f"/register/{b64}/{hash}", status=200)

    assert res.form["groups"].value == [foo_group.id]
    assert "readonly" in res.form["groups"].attrs

    res.form["password1"] = "whatever"
    res.form["password2"] = "whatever"
    res.form["given_name"] = "George"
    res.form["family_name"] = "Abitbol"

    res = res.form.submit(status=302)
    res = res.follow(status=200)

    user = models.User.get_from_login("someoneelse")
    foo_group.reload()
    assert user.groups == [foo_group]
    user.delete()
