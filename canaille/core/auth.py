from flask import current_app

from canaille.app.i18n import gettext as _
from canaille.backends import Backend


def get_user_from_login(login=None):
    from canaille.app import models

    for attr_name in current_app.config["CANAILLE"]["LOGIN_ATTRIBUTES"]:
        if user := Backend.instance.get(models.User, **{attr_name: login}):
            return user
    return None


def login_placeholder():
    """Build a placeholder string for the login form, based on the attributes users can use to identify themselves."""
    default_values = {
        "formatted_name": _("John Doe"),
        "user_name": _("jdoe"),
        "emails": _("john.doe@example.com"),
    }
    placeholders = [
        default_values[attr_name]
        for attr_name in current_app.config["CANAILLE"]["LOGIN_ATTRIBUTES"]
        if default_values.get(attr_name)
    ]
    return _(" or ").join(placeholders)
