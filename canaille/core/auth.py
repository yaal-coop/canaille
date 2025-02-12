from flask import current_app

from canaille.app.i18n import gettext as _
from canaille.backends import Backend


def get_user_from_login(login=None):
    from canaille.app import models

    login_attributes = current_app.config["CANAILLE"]["LOGIN_ATTRIBUTES"]

    if isinstance(login_attributes, list):
        for attr_name in login_attributes:
            if user := Backend.instance.get(models.User, **{attr_name: login}):
                return user

    if isinstance(login_attributes, dict):
        for attr_name, template in login_attributes.items():
            login_value = current_app.jinja_env.from_string(template).render(
                login=login
            )
            if user := Backend.instance.get(models.User, **{attr_name: login_value}):
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
