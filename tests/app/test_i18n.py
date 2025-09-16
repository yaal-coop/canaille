import pytest
from flask_babel import refresh
from werkzeug.datastructures import LanguageAccept

from canaille.app.i18n import smart_language_match


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


@pytest.mark.parametrize(
    "accept_list,available,expected",
    [
        # Regional variant fallback to base language
        (
            [("fr-FR", 1), ("en-US", 0.7), ("en", 0.3)],
            ["gl", "de", "fr", "es", "nb_NO", "en"],
            "fr",
        ),
        # Exact match with underscore variant
        (
            [("nb-NO", 1), ("en", 0.5)],
            ["gl", "de", "fr", "es", "nb_NO", "en"],
            "nb_NO",
        ),
        # Base language matches underscore variant
        (
            [("nb", 1), ("en", 0.5)],
            ["gl", "de", "fr", "es", "nb_NO", "en"],
            "nb_NO",
        ),
        # Exact match (non-English)
        (
            [("fr", 1), ("en", 0.5)],
            ["gl", "de", "fr", "es", "nb_NO", "en"],
            "fr",
        ),
        # English preference (exact match)
        (
            [("en-US", 1), ("en", 0.9), ("fr", 0.3)],
            ["gl", "de", "fr", "es", "nb_NO", "en"],
            "en",
        ),
        # No match, fallback to English
        (
            [("zh-CN", 1), ("ja-JP", 0.9)],
            ["gl", "de", "fr", "es", "nb_NO", "en"],
            "en",
        ),
    ],
)
def test_smart_language_match(accept_list, available, expected):
    accept = LanguageAccept(accept_list)
    result = smart_language_match(accept, available)
    assert result == expected
