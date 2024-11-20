import datetime

from webtest import Upload

from canaille.app import models


def test_photo(testclient, user, jpeg_photo, backend):
    user.photo = jpeg_photo
    backend.save(user)
    backend.reload(user)

    res = testclient.get("/profile/user/photo")
    assert res.body == jpeg_photo
    assert res.last_modified == user.last_modified
    etag = res.etag
    assert etag

    res = testclient.get(
        "/profile/user/photo",
        headers={
            "If-Modified-Since": (
                res.last_modified + datetime.timedelta(days=1)
            ).strftime("%a, %d %b %Y %H:%M:%S UTC")
        },
        status=304,
    )
    assert not res.body

    res = testclient.get(
        "/profile/user/photo",
        headers={"If-None-Match": etag},
        status=304,
    )
    assert not res.body


def test_photo_invalid_user(testclient, user):
    testclient.get("/profile/invalid/photo", status=404)


def test_photo_absent(testclient, user):
    assert not user.photo
    testclient.get("/profile/user/photo", status=404)


def test_photo_invalid_path(testclient, user):
    testclient.get("/profile/user/invalid", status=404)


def test_photo_on_profile_edition(
    testclient,
    logged_user,
    jpeg_photo,
    backend,
):
    # Add a photo
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    form["photo"] = Upload("logo.jpg", jpeg_photo)
    form["photo_delete"] = False
    res = form.submit(name="action", value="edit-profile")
    assert ("success", "Profile updated successfully.") in res.flashes
    res = res.follow()

    backend.reload(logged_user)

    assert logged_user.photo == jpeg_photo

    # No change
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    form["photo_delete"] = False
    res = form.submit(name="action", value="edit-profile")
    assert ("success", "Profile updated successfully.") in res.flashes
    res = res.follow()

    backend.reload(logged_user)

    assert logged_user.photo == jpeg_photo

    # Photo deletion
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    form["photo_delete"] = True
    res = form.submit(name="action", value="edit-profile")
    assert ("success", "Profile updated successfully.") in res.flashes
    res = res.follow()

    backend.reload(logged_user)

    assert logged_user.photo is None

    # Photo deletion AND upload, this should never happen
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    form["photo"] = Upload("logo.jpg", jpeg_photo)
    form["photo_delete"] = True
    res = form.submit(name="action", value="edit-profile")
    assert ("success", "Profile updated successfully.") in res.flashes
    res = res.follow()

    backend.reload(logged_user)

    assert logged_user.photo is None


def test_photo_on_profile_creation(testclient, jpeg_photo, logged_admin, backend):
    res = testclient.get("/users", status=200)
    assert backend.get(models.User, user_name="foobar") is None
    res.mustcontain(no="foobar")

    res = testclient.get("/profile", status=200)
    form = res.forms["baseform"]
    form["photo"] = Upload("logo.jpg", jpeg_photo)
    form["user_name"] = "foobar"
    form["family_name"] = "Abitbol"
    form["emails-0"] = "george@abitbol.test"
    res = form.submit(name="action", value="edit-profile", status=302).follow(
        status=200
    )

    user = backend.get(models.User, user_name="foobar")
    assert user.photo == jpeg_photo
    backend.delete(user)


def test_photo_deleted_on_profile_creation(
    testclient, jpeg_photo, logged_admin, backend
):
    res = testclient.get("/users", status=200)
    assert backend.get(models.User, user_name="foobar") is None
    res.mustcontain(no="foobar")

    res = testclient.get("/profile", status=200)
    form = res.forms["baseform"]
    form["photo"] = Upload("logo.jpg", jpeg_photo)
    form["photo_delete"] = True
    form["user_name"] = "foobar"
    form["family_name"] = "Abitbol"
    form["emails-0"] = "george@abitbol.test"
    res = form.submit(name="action", value="edit-profile", status=302).follow(
        status=200
    )

    user = backend.get(models.User, user_name="foobar")
    assert user.photo is None
    backend.delete(user)
