import datetime
import io

from itsdangerous import URLSafeSerializer
from PIL import Image
from webtest import Upload

from canaille.app import models
from canaille.core.photo import setup_photo_normalization
from canaille.core.photo import teardown_photo_normalization


def photo_url(testclient, identifier):
    serializer = URLSafeSerializer(testclient.app.config["SECRET_KEY"], salt="photo")
    return f"/photo/{serializer.dumps(identifier)}"


def photo_format(data):
    return Image.open(io.BytesIO(data)).format


def test_photo(testclient, user, jpeg_photo, backend):
    """Test that user photos can be retrieved with proper caching headers."""
    user.photo = jpeg_photo
    backend.save(user)
    backend.reload(user)

    res = testclient.get(photo_url(testclient, user.identifier))
    assert res.body == user.photo
    assert photo_format(res.body) == "JPEG"
    assert res.last_modified == user.last_modified
    etag = res.etag
    assert etag

    res = testclient.get(
        photo_url(testclient, user.identifier),
        headers={
            "If-Modified-Since": (
                res.last_modified + datetime.timedelta(days=1)
            ).strftime("%a, %d %b %Y %H:%M:%S UTC")
        },
        status=304,
    )
    assert not res.body

    res = testclient.get(
        photo_url(testclient, user.identifier),
        headers={"If-None-Match": etag},
        status=304,
    )
    assert not res.body


def test_photo_invalid_token(testclient, user):
    """Test that accessing photo with invalid token returns 404."""
    testclient.get("/photo/invalid-token", status=404)


def test_photo_nonexistent_user(testclient, user):
    """Test that accessing photo for nonexistent user returns 404."""
    testclient.get(photo_url(testclient, "nonexistent"), status=404)


def test_photo_absent(testclient, backend):
    """Test that accessing photo for user without photo returns 404."""
    from canaille.app import models

    u = models.User(
        user_name="nophoto",
        emails=["nophoto@test.test"],
        family_name="nophoto",
        formatted_name="nophoto",
    )
    backend.save(u)
    testclient.get(photo_url(testclient, u.identifier), status=404)
    backend.delete(u)


def test_photo_on_profile_edition(
    testclient,
    logged_user,
    jpeg_photo,
    backend,
):
    """Test that photos can be added, kept unchanged, and deleted during profile editing."""
    # Add a photo
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    form["photo"] = Upload("logo.jpg", jpeg_photo)
    form["photo_delete"] = False
    res = form.submit(name="action", value="edit-profile")
    assert ("success", "Profile updated successfully.") in res.flashes
    res = res.follow()

    backend.reload(logged_user)

    assert photo_format(logged_user.photo) == "JPEG"
    normalized_photo = logged_user.photo

    # No change. The photo must be left untouched, and not re-encoded.
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    form["photo_delete"] = False
    res = form.submit(name="action", value="edit-profile")
    assert ("success", "Profile updated successfully.") in res.flashes
    res = res.follow()

    backend.reload(logged_user)

    assert logged_user.photo == normalized_photo

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
    """Test that photos can be added during profile creation."""
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
    assert photo_format(user.photo) == "JPEG"
    backend.delete(user)


def test_photo_disguised_as_a_jpeg_is_refused(
    testclient, logged_user, svg_photo, backend
):
    """A SVG renamed with a JPEG extension must not make it to the database."""
    initial_photo = logged_user.photo

    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    form["photo"] = Upload("evil.jpg", svg_photo)
    form["photo_delete"] = False
    res = form.submit(name="action", value="edit-profile")

    assert (
        "error",
        "Your changes couldn't be saved. Please check the form and try again.",
    ) in res.flashes
    res.mustcontain("This file is not a supported image.")

    backend.reload(logged_user)
    assert logged_user.photo == initial_photo


def test_photo_is_converted_to_a_format_the_backend_supports(
    testclient, logged_user, png_photo, backend
):
    """PNG photos are kept as-is, except on backends that can only store JPEG."""
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    form["photo"] = Upload("logo.png", png_photo)
    form["photo_delete"] = False
    res = form.submit(name="action", value="edit-profile")
    assert ("success", "Profile updated successfully.") in res.flashes

    backend.reload(logged_user)

    expected = "PNG" if "PNG" in backend.photo_formats else "JPEG"
    assert photo_format(logged_user.photo) == expected

    res = testclient.get(photo_url(testclient, logged_user.identifier))
    assert res.content_type == f"image/{expected.lower()}"


def test_too_big_photo_is_refused(testclient, logged_user, backend):
    initial_photo = logged_user.photo

    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    form["photo"] = Upload("logo.jpg", b"\xff\xd8\xff" + b"\x00" * (5 * 1024 * 1024))
    form["photo_delete"] = False
    res = form.submit(name="action", value="edit-profile")

    assert (
        "error",
        "Your changes couldn't be saved. Please check the form and try again.",
    ) in res.flashes
    res.mustcontain("File must be between")

    backend.reload(logged_user)
    assert logged_user.photo == initial_photo


def test_photo_with_an_unservable_mimetype_is_downloaded(
    testclient, user, svg_photo, backend
):
    """Photos that predate normalization are served as downloads."""
    teardown_photo_normalization()
    user.photo = svg_photo
    backend.save(user)
    setup_photo_normalization()

    res = testclient.get(photo_url(testclient, user.identifier))
    assert res.content_type == "application/octet-stream"


def test_photo_deleted_on_profile_creation(
    testclient, jpeg_photo, logged_admin, backend
):
    """Test that photo deletion flag is respected during profile creation."""
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


def test_webp_photo_upload(testclient, logged_user, webp_photo, backend):
    """WEBP photos are accepted and converted when the backend cannot store them."""
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    form["photo"] = Upload("logo.webp", webp_photo)
    form["photo_delete"] = False
    res = form.submit(name="action", value="edit-profile")
    assert ("success", "Profile updated successfully.") in res.flashes

    backend.reload(logged_user)

    expected = "WEBP" if "WEBP" in backend.photo_formats else "JPEG"
    assert photo_format(logged_user.photo) == expected
