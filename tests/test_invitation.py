from datetime import datetime
from datetime import timedelta

from canaille.account import Invitation
from canaille.apputils import b64_to_obj
from canaille.apputils import obj_to_b64
from canaille.apputils import profile_hash
from canaille.models import User


def test_invitation(testclient, slapd_connection, logged_admin, foo_group, smtpd):
    with testclient.app.app_context():
        assert User.get("someone", conn=slapd_connection) is None

    res = testclient.get("/invite", status=200)

    res.form["uid"] = "someone"
    res.form["mail"] = "someone@domain.tld"
    res.form["groups"] = [foo_group.dn]
    res = res.form.submit(name="action", value="send", status=200)
    assert len(smtpd.messages) == 1

    url = res.pyquery("#copy-text")[0].value

    # logout
    with testclient.session_transaction() as sess:
        del sess["user_dn"]

    res = testclient.get(url, status=200)

    assert res.form["uid"].value == "someone"
    assert res.form["mail"].value == "someone@domain.tld"
    assert res.form["groups"].value == [foo_group.dn]

    res.form["password1"] = "whatever"
    res.form["password2"] = "whatever"
    res.form["givenName"] = "George"
    res.form["sn"] = "Abitbol"

    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.app.app_context():
        user = User.get("someone", conn=slapd_connection)
        user.load_groups(conn=slapd_connection)
        foo_group.reload(slapd_connection)
        assert user.check_password("whatever")
        assert user.groups == [foo_group]

    with testclient.session_transaction() as sess:
        assert "user_dn" in sess
        del sess["user_dn"]

    res = testclient.get(url, status=302)


def test_generate_link(testclient, slapd_connection, logged_admin, foo_group, smtpd):
    with testclient.app.app_context():
        assert User.get("sometwo", conn=slapd_connection) is None

    res = testclient.get("/invite", status=200)

    res.form["uid"] = "sometwo"
    res.form["mail"] = "sometwo@domain.tld"
    res.form["groups"] = [foo_group.dn]
    res = res.form.submit(name="action", value="generate", status=200)
    assert len(smtpd.messages) == 0

    url = res.pyquery("#copy-text")[0].value

    # logout
    with testclient.session_transaction() as sess:
        del sess["user_dn"]

    res = testclient.get(url, status=200)

    assert res.form["uid"].value == "sometwo"
    assert res.form["mail"].value == "sometwo@domain.tld"
    assert res.form["groups"].value == [foo_group.dn]

    res.form["password1"] = "whatever"
    res.form["password2"] = "whatever"
    res.form["givenName"] = "George"
    res.form["sn"] = "Abitbol"

    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.app.app_context():
        user = User.get("sometwo", conn=slapd_connection)
        user.load_groups(conn=slapd_connection)
        foo_group.reload(slapd_connection)
        assert user.check_password("whatever")
        assert user.groups == [foo_group]

    with testclient.session_transaction() as sess:
        assert "user_dn" in sess
        del sess["user_dn"]

    res = testclient.get(url, status=302)


def test_invitation_login_already_taken(testclient, slapd_connection, logged_admin):
    res = testclient.get("/invite", status=200)

    res.form["uid"] = logged_admin.uid
    res.form["mail"] = logged_admin.mail[0]
    res = res.form.submit(name="action", value="send", status=200)

    assert "The login &#39;admin&#39; already exists" in res.text
    assert "The email &#39;jane@doe.com&#39; already exists" in res.text


def test_registration(testclient, slapd_connection, foo_group):
    with testclient.app.app_context():
        invitation = Invitation(
            datetime.now().isoformat(),
            "someoneelse",
            "someone@mydomain.tld",
            foo_group.dn,
        )
        b64 = invitation.b64()
        hash = invitation.profile_hash()

    testclient.get(f"/register/{b64}/{hash}", status=200)


def test_registration_invalid_hash(testclient, slapd_connection, foo_group):
    with testclient.app.app_context():
        invitation = Invitation(
            datetime.now().isoformat(),
            "someoneelse",
            "someone@mydomain.tld",
            foo_group.dn,
        )
        b64 = invitation.b64()

    testclient.get(f"/register/{b64}/invalid", status=302)


def test_registration_bad_hash(testclient, slapd_connection, foo_group):
    with testclient.app.app_context():
        now = datetime.now().isoformat()
        invitation1 = Invitation(
            now, "someoneelse", "someone@mydomain.tld", foo_group.dn
        )
        hash = invitation1.profile_hash()
        invitation2 = Invitation(now, "anything", "someone@mydomain.tld", foo_group.dn)
        b64 = invitation2.b64()

    testclient.get(f"/register/{b64}/{hash}", status=302)


def test_registration_invalid_data(testclient, slapd_connection, foo_group):
    with testclient.app.app_context():
        invitation = Invitation(
            datetime.now().isoformat(),
            "someoneelse",
            "someone@mydomain.tld",
            foo_group.dn,
        )
        hash = invitation.profile_hash()

    res = testclient.get(f"/register/invalid/{hash}", status=302)


def test_registration_more_than_48_hours_after_invitation(
    testclient, slapd_connection, foo_group
):
    with testclient.app.app_context():
        two_days_ago = datetime.now() - timedelta(hours=48)
        invitation = Invitation(
            two_days_ago.isoformat(),
            "someoneelse",
            "someone@mydomain.tld",
            foo_group.dn,
        )
        hash = invitation.profile_hash()
        b64 = invitation.b64()

    testclient.get(f"/register/{b64}/{hash}", status=302)


def test_registration_no_password(testclient, slapd_connection, foo_group):
    with testclient.app.app_context():
        invitation = Invitation(
            datetime.now().isoformat(),
            "someoneelse",
            "someone@mydomain.tld",
            foo_group.dn,
        )
        hash = invitation.profile_hash()
        b64 = invitation.b64()
        url = f"/register/{b64}/{hash}"

    res = testclient.get(url, status=200)
    assert "required" in res.form["password1"].attrs
    assert "required" in res.form["password2"].attrs

    res = res.form.submit(status=200)
    assert "This field is required." in res.text, res.text

    with testclient.app.app_context():
        assert not User.get("someoneelse", conn=slapd_connection)

    with testclient.session_transaction() as sess:
        assert "user_dn" not in sess


def test_no_registration_if_logged_in(
    testclient, slapd_connection, logged_user, foo_group
):
    with testclient.app.app_context():
        invitation = Invitation(
            datetime.now().isoformat(),
            "someoneelse",
            "someone@mydomain.tld",
            foo_group.dn,
        )
        hash = invitation.profile_hash()
        b64 = invitation.b64()
        url = f"/register/{b64}/{hash}"

    testclient.get(url, status=302)


def test_unavailable_if_no_smtp(testclient, logged_admin):
    res = testclient.get("/users")
    assert "Invite a user" in res.text
    res = testclient.get("/profile")
    assert "Invite a user" in res.text
    testclient.get("/invite")

    del testclient.app.config["SMTP"]

    res = testclient.get("/users")
    assert "Invite a user" not in res.text
    res = testclient.get("/profile")
    assert "Invite a user" not in res.text
    testclient.get("/invite", status=500, expect_errors=True)
