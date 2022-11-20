from canaille.models import User


def test_preferred_language(testclient, logged_user):
    assert logged_user.preferredLanguage is None

    res = testclient.get("/profile/user", status=200)
    assert res.form["preferredLanguage"].value == "auto"
    assert "My profile" in res.text
    assert "Mon profil" not in res.text

    res.form["preferredLanguage"] = "fr"
    res = res.form.submit(name="action", value="edit").follow()
    logged_user = User.get(dn=logged_user.dn)
    assert logged_user.preferredLanguage == "fr"
    assert res.form["preferredLanguage"].value == "fr"
    assert "My profile" not in res.text
    assert "Mon profil" in res.text

    res.form["preferredLanguage"] = "en"
    res = res.form.submit(name="action", value="edit").follow()
    logged_user = User.get(dn=logged_user.dn)
    assert logged_user.preferredLanguage == "en"
    assert res.form["preferredLanguage"].value == "en"
    assert "My profile" in res.text
    assert "Mon profil" not in res.text

    res.form["preferredLanguage"] = "auto"
    res = res.form.submit(name="action", value="edit").follow()
    logged_user = User.get(dn=logged_user.dn)
    assert logged_user.preferredLanguage is None
    assert res.form["preferredLanguage"].value == "auto"
    assert "My profile" in res.text
    assert "Mon profil" not in res.text


def test_language_config(testclient, logged_user):
    res = testclient.get("/profile/user", status=200)
    assert "My profile" in res.text
    assert "Mon profil" not in res.text

    testclient.app.config["LANGUAGE"] = "fr"
    res = testclient.get("/profile/user", status=200)
    assert "My profile" not in res.text
    assert "Mon profil" in res.text
