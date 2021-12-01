from canaille.models import User
from canaille.apputils import profile_hash, obj_to_b64


def test_invitation(testclient, slapd_connection, logged_admin, foo_group):
    with testclient.app.app_context():
        assert User.get("someone", conn=slapd_connection) is None

    res = testclient.get("/invite", status=200)

    res.form["uid"] = "someone"
    res.form["mail"] = "someone@domain.tld"
    res.form["groups"] = [foo_group.dn]
    res = res.form.submit(status=200)
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
        assert User.get("someone", conn=slapd_connection)

    with testclient.session_transaction() as sess:
        assert "user_dn" in sess
        del sess["user_dn"]

    res = testclient.get(url, status=302)


def test_invitation_login_already_taken(testclient, slapd_connection, logged_admin):
    res = testclient.get("/invite", status=200)

    res.form["uid"] = logged_admin.uid
    res.form["mail"] = logged_admin.mail[0]
    res = res.form.submit(status=200)

    assert "The login 'admin' already exists" in res.text
    assert "The email 'jane@doe.com' already exists" in res.text


def test_registration_invalid_data(testclient, slapd_connection, foo_group):
    with testclient.app.app_context():
        data = ["someoneelse", "someone@mydomain.tld", foo_group.dn]
        b64 = obj_to_b64(data)

    testclient.get(f"/register/{b64}/invalid", status=302)


def test_registration_invalid_hash(testclient, slapd_connection, foo_group):
    with testclient.app.app_context():
        data = ["someoneelse", "someone@mydomain.tld", foo_group.dn]
        hash = profile_hash(*data)
        data = ["anything", "someone@mydomain.tld", foo_group.dn]
        b64 = obj_to_b64(data)

    testclient.get(f"/register/{b64}/{hash}", status=302)


def test_registration_bad_hash(testclient, slapd_connection, foo_group):
    with testclient.app.app_context():
        data = ["someoneelse", "someone@mydomain.tld", foo_group.dn]
        hash = profile_hash(*data)

    testclient.get(f"/register/invalid/{hash}", status=302)


def test_registration_no_password(testclient, slapd_connection, foo_group):
    with testclient.app.app_context():
        data = ["someoneelse", "someone@mydomain.tld", foo_group.dn]
        hash = profile_hash(*data)
        b64 = obj_to_b64(data)
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
        data = ["anyone", "someone@mydomain.tld", foo_group.dn]
        hash = profile_hash(*data)
        b64 = obj_to_b64(data)
        url = f"/register/{b64}/{hash}"

    testclient.get(url, status=302)
