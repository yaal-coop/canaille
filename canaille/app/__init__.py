import base64
import hashlib
import json
import re

from canaille.core.models import User
from flask import current_app
from flask import request
from flask_babel import gettext as _


def obj_to_b64(obj):
    return base64.b64encode(json.dumps(obj).encode("utf-8")).decode("utf-8")


def b64_to_obj(string):
    return json.loads(base64.b64decode(string.encode("utf-8")).decode("utf-8"))


def profile_hash(*args):
    return hashlib.sha256(
        current_app.config["SECRET_KEY"].encode("utf-8")
        + obj_to_b64(args).encode("utf-8")
    ).hexdigest()


def login_placeholder():
    user_filter = current_app.config["BACKENDS"]["LDAP"].get(
        "USER_FILTER", User.DEFAULT_FILTER
    )
    placeholders = []

    if "cn={login}" in user_filter:
        placeholders.append(_("John Doe"))

    if "uid={login}" in user_filter:
        placeholders.append(_("jdoe"))

    if "mail={login}" in user_filter or not placeholders:
        placeholders.append(_("john@doe.com"))

    return _(" or ").join(placeholders)


def default_fields():
    read = set()
    write = set()
    for acl in current_app.config["ACL"].values():
        if "FILTER" not in acl:
            read |= set(acl.get("READ", []))
            write |= set(acl.get("WRITE", []))

    return read, write


def get_current_domain():
    if current_app.config.get("SERVER_NAME"):
        return current_app.config.get("SERVER_NAME")

    return request.host


def get_current_mail_domain():
    if current_app.config["SMTP"].get("FROM_ADDR"):
        return current_app.config["SMTP"]["FROM_ADDR"].split("@")[-1]

    return get_current_domain()


def validate_uri(value):
    regex = re.compile(
        r"^(?:[A-Z0-9\\.-]+)s?://"  # scheme + ://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
        r"[A-Z0-9\\.-]+|"  # hostname...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return re.match(regex, value) is not None
