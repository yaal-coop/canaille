import datetime

from canaille.models import User
from webtest import Upload


def test_photo(testclient, user, jpeg_photo):
    user.jpegPhoto = [jpeg_photo]
    user.save()
    user = User.get(id=user.id)

    res = testclient.get("/profile/user/jpegPhoto")
    assert res.body == jpeg_photo
    assert res.last_modified == user.modifyTimestamp
    etag = res.etag
    assert etag

    res = testclient.get(
        "/profile/user/jpegPhoto",
        headers={
            "If-Modified-Since": (
                res.last_modified + datetime.timedelta(days=1)
            ).strftime("%a, %d %b %Y %H:%M:%S UTC")
        },
        status=304,
    )
    assert not res.body

    res = testclient.get(
        "/profile/user/jpegPhoto",
        headers={"If-None-Match": etag},
        status=304,
    )
    assert not res.body


def test_photo_invalid_user(testclient, user):
    res = testclient.get("/profile/invalid/jpegPhoto", status=404)


def test_photo_absent(testclient, user):
    assert not user.jpegPhoto
    res = testclient.get("/profile/user/jpegPhoto", status=404)


def test_photo_invalid_path(testclient, user):
    testclient.get("/profile/user/invalid", status=404)


def test_photo_on_profile_edition(
    testclient,
    slapd_server,
    logged_user,
    jpeg_photo,
):
    # Add a photo
    res = testclient.get("/profile/user", status=200)
    res.form["jpegPhoto"] = Upload("logo.jpg", jpeg_photo)
    res.form["jpegPhoto_delete"] = False
    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfuly.") in res.flashes
    res = res.follow()

    logged_user = User.get(id=logged_user.id)

    assert [jpeg_photo] == logged_user.jpegPhoto

    # No change
    res = testclient.get("/profile/user", status=200)
    res.form["jpegPhoto_delete"] = False
    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfuly.") in res.flashes
    res = res.follow()

    logged_user = User.get(id=logged_user.id)

    assert [jpeg_photo] == logged_user.jpegPhoto

    # Photo deletion
    res = testclient.get("/profile/user", status=200)
    res.form["jpegPhoto_delete"] = True
    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfuly.") in res.flashes
    res = res.follow()

    logged_user = User.get(id=logged_user.id)

    assert [] == logged_user.jpegPhoto

    # Photo deletion AND upload, this should never happen
    res = testclient.get("/profile/user", status=200)
    res.form["jpegPhoto"] = Upload("logo.jpg", jpeg_photo)
    res.form["jpegPhoto_delete"] = True
    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfuly.") in res.flashes
    res = res.follow()

    logged_user = User.get(id=logged_user.id)

    assert [] == logged_user.jpegPhoto


def test_photo_on_profile_creation(testclient, slapd_server, jpeg_photo, logged_admin):
    res = testclient.get("/users", status=200)
    assert User.get("foobar") is None
    res.mustcontain(no="foobar")

    res = testclient.get("/profile", status=200)
    res.form["jpegPhoto"] = Upload("logo.jpg", jpeg_photo)
    res.form["uid"] = "foobar"
    res.form["sn"] = "Abitbol"
    res.form["mail"] = "george@abitbol.com"
    res = res.form.submit(name="action", value="edit", status=302).follow(status=200)

    user = User.get("foobar")
    assert user.jpegPhoto == [jpeg_photo]
    user.delete()


def test_photo_deleted_on_profile_creation(
    testclient, slapd_server, jpeg_photo, logged_admin
):
    res = testclient.get("/users", status=200)
    assert User.get("foobar") is None
    res.mustcontain(no="foobar")

    res = testclient.get("/profile", status=200)
    res.form["jpegPhoto"] = Upload("logo.jpg", jpeg_photo)
    res.form["jpegPhoto_delete"] = True
    res.form["uid"] = "foobar"
    res.form["sn"] = "Abitbol"
    res.form["mail"] = "george@abitbol.com"
    res = res.form.submit(name="action", value="edit", status=302).follow(status=200)

    user = User.get("foobar")
    assert user.jpegPhoto == []
    user.delete()
