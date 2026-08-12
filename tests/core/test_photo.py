import io

import pytest
from PIL import Image

from canaille.core.photo import InvalidPhotoError
from canaille.core.photo import normalize_photo
from canaille.core.utils import guess_image_mimetype
from tests.conftest import make_photo

SQL_FORMATS = ("WEBP", "PNG", "JPEG")
LDAP_FORMATS = ("JPEG",)


def open_photo(data):
    return Image.open(io.BytesIO(data))


def test_normalize_keeps_the_input_format_when_supported(jpeg_photo, png_photo):
    """Photos are stored in their own format when the backend supports it."""
    assert open_photo(normalize_photo(jpeg_photo, SQL_FORMATS)).format == "JPEG"
    assert open_photo(normalize_photo(png_photo, SQL_FORMATS)).format == "PNG"
    assert open_photo(normalize_photo(make_photo("WEBP"), SQL_FORMATS)).format == "WEBP"


def test_normalize_falls_back_on_the_first_supported_format(png_photo):
    """Photos are converted when the backend cannot store their own format."""
    assert open_photo(normalize_photo(png_photo, LDAP_FORMATS)).format == "JPEG"
    assert open_photo(normalize_photo(png_photo, ("WEBP",))).format == "WEBP"


def test_normalize_flattens_transparency_on_opaque_formats(png_photo):
    """Transparency is composed over white, as JPEG would render it black."""
    image = open_photo(normalize_photo(png_photo, LDAP_FORMATS))
    assert image.mode == "RGB"

    transparent = make_photo("PNG", mode="RGBA", color=(0, 0, 0, 0))
    image = open_photo(normalize_photo(transparent, LDAP_FORMATS))
    assert image.getpixel((0, 0)) == (255, 255, 255)


def test_normalize_keeps_transparency_on_alpha_capable_formats():
    transparent = make_photo("PNG", mode="RGBA", color=(0, 0, 0, 0))
    image = open_photo(normalize_photo(transparent, SQL_FORMATS))
    assert image.mode == "RGBA"
    assert image.getpixel((0, 0))[3] == 0


def test_normalize_downscales_and_keeps_the_ratio():
    photo = make_photo("JPEG", size=(2000, 1000))
    image = open_photo(normalize_photo(photo, SQL_FORMATS))
    assert image.size == (1024, 512)


def test_normalize_does_not_upscale_small_photos():
    image = open_photo(normalize_photo(make_photo("JPEG", size=(32, 16)), SQL_FORMATS))
    assert image.size == (32, 16)


def test_normalize_strips_metadata():
    """EXIF tags, which hold the GPS coordinates of smartphone photos, are dropped."""
    exif = Image.Exif()
    exif[0x010E] = "a description"
    photo = make_photo("JPEG", exif=exif)
    assert Image.open(io.BytesIO(photo)).getexif()

    image = open_photo(normalize_photo(photo, SQL_FORMATS))
    assert not image.getexif()


def test_normalize_applies_the_exif_orientation():
    """The EXIF orientation is applied before metadata is dropped."""
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90°
    photo = make_photo("JPEG", size=(40, 20), exif=exif)

    image = open_photo(normalize_photo(photo, SQL_FORMATS))
    assert image.size == (20, 40)


def test_normalize_refuses_svg(svg_photo):
    with pytest.raises(InvalidPhotoError):
        normalize_photo(svg_photo, SQL_FORMATS)


def test_normalize_refuses_unsupported_formats():
    """Formats Pillow can decode are still refused when they are not allowed."""
    with pytest.raises(InvalidPhotoError):
        normalize_photo(make_photo("GIF"), SQL_FORMATS)

    with pytest.raises(InvalidPhotoError):
        normalize_photo(make_photo("BMP"), SQL_FORMATS)


def test_normalize_refuses_truncated_photos():
    """A photo with a valid header but incomplete data cannot be decoded."""
    photo = make_photo("JPEG", size=(200, 200))

    with pytest.raises(InvalidPhotoError):
        normalize_photo(photo[: len(photo) // 2], SQL_FORMATS)


def test_normalize_refuses_garbage():
    with pytest.raises(InvalidPhotoError):
        normalize_photo(b"this is not an image", SQL_FORMATS)

    with pytest.raises(InvalidPhotoError):
        normalize_photo(b"", SQL_FORMATS)


@pytest.mark.filterwarnings("ignore::PIL.Image.DecompressionBombWarning")
def test_normalize_refuses_decompression_bombs():
    """A small file declaring huge dimensions is refused before it is decoded."""
    photo = make_photo("PNG", size=(10000, 10000), mode="1", color=0)
    assert len(photo) < 100_000

    with pytest.raises(InvalidPhotoError):
        normalize_photo(photo, SQL_FORMATS, max_size=(1, 1))


def test_photos_are_refused_without_pillow(monkeypatch, jpeg_photo):
    """Photos are not supported at all in installations without the front extras."""
    monkeypatch.setattr("canaille.core.photo.HAS_PILLOW", False)

    with pytest.raises(InvalidPhotoError):
        normalize_photo(jpeg_photo, SQL_FORMATS)


@pytest.mark.parametrize(
    "photo,expected",
    [
        (make_photo("JPEG"), "image/jpeg"),
        (make_photo("PNG"), "image/png"),
        (make_photo("WEBP"), "image/webp"),
        (make_photo("GIF"), "image/gif"),
    ],
)
def test_guess_image_mimetype(photo, expected):
    assert guess_image_mimetype(photo) == expected


@pytest.mark.parametrize(
    "data",
    [
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"/>',
        b"<html><script>alert(1)</script></html>",
        b"",
    ],
)
def test_guess_image_mimetype_refuses_interpretable_content(data):
    """Content browsers could render is served as a download instead."""
    assert guess_image_mimetype(data) == "application/octet-stream"
