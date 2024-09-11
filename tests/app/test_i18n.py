from flask_babel import refresh


def test_preferred_language(testclient, logged_user, backend):
    logged_user.preferred_language = None
    backend.save(logged_user)

    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    assert form["preferred_language"].value == "auto"
    assert res.pyquery("html")[0].attrib["lang"] == "en"
    res.mustcontain("My profile")
    res.mustcontain(no="Mon profil")

    form["preferred_language"] = "fr"
    res = form.submit(name="action", value="edit-profile")
    assert res.flashes == [("success", "Le profil a été mis à jour avec succès.")]
    res = res.follow()
    form = res.forms["baseform"]
    backend.reload(logged_user)
    assert logged_user.preferred_language == "fr"
    assert form["preferred_language"].value == "fr"
    assert res.pyquery("html")[0].attrib["lang"] == "fr"
    res.mustcontain(no="My profile")
    res.mustcontain("Mon profil")

    form["preferred_language"] = "en"
    res = form.submit(name="action", value="edit-profile")
    assert res.flashes == [("success", "Profile updated successfully.")]
    res = res.follow()
    form = res.forms["baseform"]
    backend.reload(logged_user)
    assert logged_user.preferred_language == "en"
    assert form["preferred_language"].value == "en"
    assert res.pyquery("html")[0].attrib["lang"] == "en"
    res.mustcontain("My profile")
    res.mustcontain(no="Mon profil")

    form["preferred_language"] = "auto"
    res = form.submit(name="action", value="edit-profile")
    assert res.flashes == [("success", "Profile updated successfully.")]
    res = res.follow()
    form = res.forms["baseform"]
    backend.reload(logged_user)
    assert logged_user.preferred_language is None
    assert form["preferred_language"].value == "auto"
    assert res.pyquery("html")[0].attrib["lang"] == "en"
    res.mustcontain("My profile")
    res.mustcontain(no="Mon profil")


def test_form_translations(testclient, logged_user, backend):
    logged_user.preferred_language = "fr"
    backend.save(logged_user)

    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    form["phone_numbers-0"] = "invalid"
    res = form.submit(name="action", value="edit-profile")

    res.mustcontain(no="Not a valid phone number")
    res.mustcontain("N’est pas un numéro de téléphone valid")


def test_language_config(testclient, logged_user, backend):
    logged_user.preferred_language = None
    backend.save(logged_user)

    res = testclient.get("/profile/user", status=200)
    assert res.pyquery("html")[0].attrib["lang"] == "en"
    res.mustcontain("My profile")
    res.mustcontain(no="Mon profil")

    testclient.app.config["CANAILLE"]["LANGUAGE"] = "fr"
    refresh()
    res = testclient.get("/profile/user", status=200)
    assert res.pyquery("html")[0].attrib["lang"] == "fr"
    res.mustcontain(no="My profile")
    res.mustcontain("Mon profil")
