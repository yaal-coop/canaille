import base64
import email.message
import hashlib
import json
import logging
import mimetypes
import smtplib
import urllib.request
from email.utils import make_msgid

from canaille.models import User
from flask import current_app
from flask import request
from flask_babel import gettext as _

DEFAULT_SMTP_HOST = "localhost"
DEFAULT_SMTP_PORT = 25
DEFAULT_SMTP_TLS = False


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
    user_filter = current_app.config["LDAP"].get("USER_FILTER", User.DEFAULT_FILTER)
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
    if current_app.config["SMTP"].get("FROM_ADDR"):
        return current_app.config["SMTP"]["FROM_ADDR"].split("@")[-1]

    elif current_app.config.get("SERVER_NAME"):
        return current_app.config.get("SERVER_NAME")

    return request.host


def logo():
    logo_url = current_app.config.get("LOGO")
    if not logo_url:
        return None, None, None

    logo_filename = logo_url.split("/")[-1]
    if not logo_url.startswith("http"):
        if current_app.config.get("SERVER_NAME"):
            logo_url = "{}://{}/{}".format(
                current_app.config.get("PREFERRED_URL_SCHEME"),
                current_app.config.get("SERVER_NAME"),
                logo_url,
            )
        else:
            logo_url = f"{request.url_root}{logo_url}"

    try:
        with urllib.request.urlopen(logo_url) as f:
            logo_raw = f.read()
    except (urllib.error.HTTPError, urllib.error.URLError):
        logo_filename = None
        logo_raw = None

    logo_cid = make_msgid(domain=get_current_domain())
    return logo_cid, logo_filename, logo_raw


def send_email(subject, recipient, text, html, attachements=None):
    msg = email.message.EmailMessage()
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    msg["Subject"] = subject
    msg["To"] = f"<{recipient}>"

    name = current_app.config.get("NAME", "Canaille")
    address = current_app.config["SMTP"].get("FROM_ADDR")

    if not address:
        domain = get_current_domain()
        address = f"admin@{domain}"

    msg["From"] = f'"{name}" <{address}>'

    attachements = attachements or []
    for cid, filename, value in attachements:
        maintype, subtype = mimetypes.guess_type(filename)[0].split("/")
        msg.get_payload()[1].add_related(
            value, maintype=maintype, subtype=subtype, cid=cid
        )
    try:
        with smtplib.SMTP(
            host=current_app.config["SMTP"].get("HOST", DEFAULT_SMTP_HOST),
            port=current_app.config["SMTP"].get("PORT", DEFAULT_SMTP_PORT),
        ) as smtp:
            if current_app.config["SMTP"].get("TLS", DEFAULT_SMTP_TLS):
                smtp.starttls()
            if current_app.config["SMTP"].get("LOGIN"):
                smtp.login(
                    user=current_app.config["SMTP"].get("LOGIN"),
                    password=current_app.config["SMTP"].get("PASSWORD"),
                )
            smtp.send_message(msg)

    except smtplib.SMTPRecipientsRefused:
        pass

    except OSError as exc:
        logging.exception(f"Could not send email: {exc}")
        return False

    return True
