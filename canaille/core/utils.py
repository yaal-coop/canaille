IMAGE_SIGNATURES = (
    (b"\xff\xd8\xff", "JPEG"),
    (b"\x89PNG", "PNG"),
    (b"GIF87a", "GIF"),
    (b"GIF89a", "GIF"),
)

FORMAT_MIMETYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}

DEFAULT_MIMETYPE = "application/octet-stream"


def guess_image_format(data: bytes) -> str | None:
    """Detect an image format from its magic bytes.

    :param data: Image data as bytes
    :return: The format name, or :py:data:`None` when it is not a known image
    """
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "WEBP"

    for signature, format in IMAGE_SIGNATURES:
        if data.startswith(signature):
            return format

    return None


def guess_image_mimetype(data: bytes) -> str:
    """Detect the MIME type an image can be served with.

    Data that is not a known image format, such as SVG, gets the
    :data:`DEFAULT_MIMETYPE` so browsers download it instead of rendering it.

    :param data: Image data as bytes
    :return: The MIME type string
    """
    format = guess_image_format(data)
    return FORMAT_MIMETYPES[format] if format else DEFAULT_MIMETYPE
