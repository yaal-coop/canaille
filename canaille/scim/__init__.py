from flask import url_for


def scim_base_url():
    """Return the base URL of the SCIM server."""
    return url_for("scim.scim", path="", _external=True).rstrip("/")
