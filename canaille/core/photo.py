import io

from blinker import signal

from canaille.backends import Backend

ALLOWED_INPUT_FORMATS = {"JPEG", "PNG", "WEBP"}
"""Image formats users are allowed to upload."""

ALPHA_CAPABLE_FORMATS = {"PNG", "WEBP"}
"""Formats able to store an alpha channel."""

MAX_PHOTO_SIZE = (1024, 1024)
"""Maximum photo dimensions. Bigger photos are downscaled, keeping their ratio."""

PHOTO_QUALITY = 85

MAX_PHOTO_PIXELS = 50_000_000
"""Maximum amount of pixels an uploaded image can hold, so a small file cannot
allocate gigabytes at decoding time."""

MAX_PHOTO_UPLOAD_SIZE = 5 * 1024 * 1024
"""Maximum size in bytes of an uploaded photo."""

try:
    from PIL import Image
    from PIL import ImageOps

    Image.MAX_IMAGE_PIXELS = MAX_PHOTO_PIXELS
    HAS_PILLOW = True
except ImportError:  # pragma: no cover
    HAS_PILLOW = False


class InvalidPhotoError(ValueError):
    """Raised when photo data cannot be used as a profile photo."""


def check_photo(data: bytes) -> str:
    """Check that data can be stored as a photo, and return its format.

    :raises InvalidPhotoError: when the data cannot be used as a profile photo.
    """
    return _open_photo(data).format


def normalize_photo(
    data: bytes, formats: tuple[str, ...], max_size: tuple[int, int] = MAX_PHOTO_SIZE
) -> bytes:
    """Decode, sanitize and re-encode an image into a format the backend accepts.

    The image is stripped from its metadata, downscaled to *max_size* and encoded
    in its original format when *formats* allows it, or in ``formats[0]``.
    """
    image = _open_photo(data)
    target_format = image.format if image.format in formats else formats[0]

    try:
        image.load()
    except Exception as exc:
        raise InvalidPhotoError("The image could not be decoded.") from exc

    image = ImageOps.exif_transpose(image)
    image.thumbnail(max_size)
    image = _convert(image, target_format)

    output = io.BytesIO()
    image.save(output, format=target_format, quality=PHOTO_QUALITY)
    return output.getvalue()


def _open_photo(data: bytes):
    if not HAS_PILLOW:
        raise InvalidPhotoError(
            "Photos need Pillow, which comes with the 'front' packaging extras."
        )

    try:
        image = Image.open(io.BytesIO(data))
    except Exception as exc:
        raise InvalidPhotoError("The image format could not be read.") from exc

    if image.format not in ALLOWED_INPUT_FORMATS:
        raise InvalidPhotoError(f"Unsupported image format: {image.format}")

    if image.width * image.height > MAX_PHOTO_PIXELS:
        raise InvalidPhotoError("The image is too large to be decoded.")

    return image


def _convert(image, target_format):
    """Put an image in a mode the target format can encode."""
    has_alpha = image.mode in ("RGBA", "LA") or "transparency" in image.info
    if not has_alpha:
        return image.convert("RGB")

    if target_format in ALPHA_CAPABLE_FORMATS:
        return image.convert("RGBA")

    image = image.convert("RGBA")
    background = Image.new("RGB", image.size, "white")
    background.paste(image, mask=image.getchannel("A"))
    return background


def normalize_user_photo(user, data):
    """Normalize user photos when they change.

    Unchanged photos are skipped, as re-encoding them on every user save would
    degrade the image a bit more at each login.
    """
    if not user.photo:
        return

    if user.photo == Backend.instance.get_persisted_value(user, "photo"):
        return

    user.photo = normalize_photo(user.photo, Backend.instance.photo_formats)


def setup_photo_normalization():
    teardown_photo_normalization()
    signal("before_user_save").connect(normalize_user_photo)


def teardown_photo_normalization():
    signal("before_user_save").disconnect(normalize_user_photo)
