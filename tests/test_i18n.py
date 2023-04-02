from canaille.models import User
from flask_babel import refresh


def test_preferred_language(slapd_server, testclient, logged_user):
    logged_user.preferredLanguage = None
    logged_user.save()

    res = testclient.get("/profile/user", status=200)
    assert res.form["preferredLanguage"].value == "auto"
    assert res.pyquery("html")[0].attrib["lang"] == "en"
    res.mustcontain("My profile")
    res.mustcontain(no="Mon profil")

    res.form["preferredLanguage"] = "fr"
    res = res.form.submit(name="action", value="edit")
    assert res.flashes == [("success", "Le profil a été mis à jour avec succès.")]
    res = res.follow()
    logged_user = User.get(id=logged_user.id)
    assert logged_user.preferredLanguage == "fr"
    assert res.form["preferredLanguage"].value == "fr"
    assert res.pyquery("html")[0].attrib["lang"] == "fr"
    res.mustcontain(no="My profile")
    res.mustcontain("Mon profil")

    res.form["preferredLanguage"] = "en"
    res = res.form.submit(name="action", value="edit")
    assert res.flashes == [("success", "Profile updated successfuly.")]
    res = res.follow()
    logged_user = User.get(id=logged_user.id)
    assert logged_user.preferredLanguage == "en"
    assert res.form["preferredLanguage"].value == "en"
    assert res.pyquery("html")[0].attrib["lang"] == "en"
    res.mustcontain("My profile")
    res.mustcontain(no="Mon profil")

    res.form["preferredLanguage"] = "auto"
    res = res.form.submit(name="action", value="edit")
    assert res.flashes == [("success", "Profile updated successfuly.")]
    res = res.follow()
    logged_user = User.get(id=logged_user.id)
    assert logged_user.preferredLanguage is None
    assert res.form["preferredLanguage"].value == "auto"
    assert res.pyquery("html")[0].attrib["lang"] == "en"
    res.mustcontain("My profile")
    res.mustcontain(no="Mon profil")


def test_form_translations(slapd_server, testclient, logged_user):
    logged_user.preferredLanguage = "fr"
    logged_user.save()

    res = testclient.get("/profile/user", status=200)
    res.form["mail"] = "invalid"
    res = res.form.submit(name="action", value="edit")

    res.mustcontain(no="Invalid email address.")
    res.mustcontain("Adresse électronique non valide.")


def test_language_config(testclient, logged_user):
    logged_user.preferredLanguage = None
    logged_user.save()

    res = testclient.get("/profile/user", status=200)
    assert res.pyquery("html")[0].attrib["lang"] == "en"
    res.mustcontain("My profile")
    res.mustcontain(no="Mon profil")

    testclient.app.config["LANGUAGE"] = "fr"
    refresh()
    res = testclient.get("/profile/user", status=200)
    assert res.pyquery("html")[0].attrib["lang"] == "fr"
    res.mustcontain(no="My profile")
    res.mustcontain("Mon profil")
