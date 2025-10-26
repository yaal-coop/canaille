def guess_image_mimetype(data: bytes) -> str:  # pragma: no cover
    """Detect image MIME type from magic bytes.

    :param data: Image data as bytes
    :return: The MIME type string, or 'application/octet-stream' if type cannot be determined
    """
    if data.startswith(b"<svg") or data.startswith(b"<?xml"):
        return "image/svg+xml"
    elif data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif data.startswith(b"\x89PNG"):
        return "image/png"
    elif data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    else:
        return "application/octet-stream"
