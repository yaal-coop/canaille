import base64
import urllib.request
from flask import current_app, request


def base64logo():
    logo_url = current_app.config.get("LOGO")
    if not logo_url:
        return None, None

    logo_extension = logo_url.split(".")[-1]
    if not logo_url.startswith("http"):
        if current_app.config.get("SERVER_NAME"):
            logo_url = "{}://{}/{}".format(
                current_app.config.get("PREFERRED_URL_SCHEME"),
                current_app.config.get("SERVER_NAME"),
                logo_url,
            )
        else:
            logo_url = "{}{}".format(request.url_root, logo_url)

    try:
        with urllib.request.urlopen(logo_url) as f:
            logo = base64.b64encode(f.read()).decode("utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError):
        logo = None
        logo_extension = None

    return logo, logo_extension
