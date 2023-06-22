import datetime

from canaille.app import models
from webtest import Upload


def test_photo(testclient, user, jpeg_photo):
    user.photo = [jpeg_photo]
    user.save()
    user.reload()

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
):
    # Add a photo
    res = testclient.get("/profile/user", status=200)
    res.form["photo"] = Upload("logo.jpg", jpeg_photo)
    res.form["photo_delete"] = False
    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfully.") in res.flashes
    res = res.follow()

    logged_user.reload()

    assert [jpeg_photo] == logged_user.photo

    # No change
    res = testclient.get("/profile/user", status=200)
    res.form["photo_delete"] = False
    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfully.") in res.flashes
    res = res.follow()

    logged_user.reload()

    assert [jpeg_photo] == logged_user.photo

    # Photo deletion
    res = testclient.get("/profile/user", status=200)
    res.form["photo_delete"] = True
    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfully.") in res.flashes
    res = res.follow()

    logged_user.reload()

    assert logged_user.photo == []

    # Photo deletion AND upload, this should never happen
    res = testclient.get("/profile/user", status=200)
    res.form["photo"] = Upload("logo.jpg", jpeg_photo)
    res.form["photo_delete"] = True
    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfully.") in res.flashes
    res = res.follow()

    logged_user.reload()

    assert [] == logged_user.photo


def test_photo_on_profile_creation(testclient, jpeg_photo, logged_admin):
    res = testclient.get("/users", status=200)
    assert models.User.get_from_login("foobar") is None
    res.mustcontain(no="foobar")

    res = testclient.get("/profile", status=200)
    res.form["photo"] = Upload("logo.jpg", jpeg_photo)
    res.form["user_name"] = "foobar"
    res.form["family_name"] = "Abitbol"
    res.form["emails"] = "george@abitbol.com"
    res = res.form.submit(name="action", value="edit", status=302).follow(status=200)

    user = models.User.get_from_login("foobar")
    assert user.photo == [jpeg_photo]
    user.delete()


def test_photo_deleted_on_profile_creation(testclient, jpeg_photo, logged_admin):
    res = testclient.get("/users", status=200)
    assert models.User.get_from_login("foobar") is None
    res.mustcontain(no="foobar")

    res = testclient.get("/profile", status=200)
    res.form["photo"] = Upload("logo.jpg", jpeg_photo)
    res.form["photo_delete"] = True
    res.form["user_name"] = "foobar"
    res.form["family_name"] = "Abitbol"
    res.form["emails"] = "george@abitbol.com"
    res = res.form.submit(name="action", value="edit", status=302).follow(status=200)

    user = models.User.get_from_login("foobar")
    assert user.photo == []
    user.delete()
