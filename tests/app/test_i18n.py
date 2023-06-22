from flask_babel import refresh


def test_preferred_language(testclient, logged_user):
    logged_user.preferred_language = None
    logged_user.save()

    res = testclient.get("/profile/user", status=200)
    assert res.form["preferred_language"].value == "auto"
    assert res.pyquery("html")[0].attrib["lang"] == "en"
    res.mustcontain("My profile")
    res.mustcontain(no="Mon profil")

    res.form["preferred_language"] = "fr"
    res = res.form.submit(name="action", value="edit")
    assert res.flashes == [("success", "Le profil a été mis à jour avec succès.")]
    res = res.follow()
    logged_user.reload()
    assert logged_user.preferred_language == "fr"
    assert res.form["preferred_language"].value == "fr"
    assert res.pyquery("html")[0].attrib["lang"] == "fr"
    res.mustcontain(no="My profile")
    res.mustcontain("Mon profil")

    res.form["preferred_language"] = "en"
    res = res.form.submit(name="action", value="edit")
    assert res.flashes == [("success", "Profile updated successfully.")]
    res = res.follow()
    logged_user.reload()
    assert logged_user.preferred_language == "en"
    assert res.form["preferred_language"].value == "en"
    assert res.pyquery("html")[0].attrib["lang"] == "en"
    res.mustcontain("My profile")
    res.mustcontain(no="Mon profil")

    res.form["preferred_language"] = "auto"
    res = res.form.submit(name="action", value="edit")
    assert res.flashes == [("success", "Profile updated successfully.")]
    res = res.follow()
    logged_user.reload()
    assert logged_user.preferred_language is None
    assert res.form["preferred_language"].value == "auto"
    assert res.pyquery("html")[0].attrib["lang"] == "en"
    res.mustcontain("My profile")
    res.mustcontain(no="Mon profil")


def test_form_translations(testclient, logged_user):
    logged_user.preferred_language = "fr"
    logged_user.save()

    res = testclient.get("/profile/user", status=200)
    res.form["emails-0"] = "invalid"
    res = res.form.submit(name="action", value="edit")

    res.mustcontain(no="Invalid email address.")
    res.mustcontain("Adresse électronique non valide.")


def test_language_config(testclient, logged_user):
    logged_user.preferred_language = None
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
