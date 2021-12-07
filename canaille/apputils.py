import base64
import email.message
import hashlib
import json
import logging
import mimetypes
import smtplib
import urllib.request
from email.utils import make_msgid
from flask import current_app, request
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
    user_filter = current_app.config["LDAP"]["USER_FILTER"]
    placeholders = []

    if "cn={login}" in user_filter:
        placeholders.append(_("John Doe"))

    if "uid={login}" in user_filter:
        placeholders.append(_("jdoe"))

    if "mail={login}" in user_filter or not placeholders:
        placeholders.append(_("john@doe.com"))

    return _(" or ").join(placeholders)


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
            logo_url = "{}{}".format(request.url_root, logo_url)

    try:
        with urllib.request.urlopen(logo_url) as f:
            logo_raw = f.read()
    except (urllib.error.HTTPError, urllib.error.URLError):
        logo_filename = None
        logo_raw = None

    domain = current_app.config["SMTP"]["FROM_ADDR"].split("@")[-1]
    logo_cid = make_msgid(domain=domain)
    return logo_cid, logo_filename, logo_raw


def send_email(subject, recipient, text, html, sender=None, attachements=None):
    msg = email.message.EmailMessage()
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    msg["Subject"] = subject
    msg["To"] = recipient

    if sender:
        msg["From"] = sender
    elif current_app.config.get("NAME"):
        msg["From"] = '"{}" <{}>'.format(
            current_app.config.get("NAME"), current_app.config["SMTP"]["FROM_ADDR"]
        )
    else:
        msg["From"] = current_app.config["SMTP"]["FROM_ADDR"]

    attachements = attachements or []
    for cid, filename, value in attachements:
        maintype, subtype = mimetypes.guess_type(filename)[0].split("/")
        msg.get_payload()[1].add_related(
            value, maintype=maintype, subtype=subtype, cid=cid
        )
    try:
        with smtplib.SMTP(
            host=current_app.config["SMTP"]["HOST"],
            port=current_app.config["SMTP"]["PORT"],
        ) as smtp:
            if current_app.config["SMTP"].get("TLS"):
                smtp.starttls()
            if current_app.config["SMTP"].get("LOGIN"):
                smtp.login(
                    user=current_app.config["SMTP"]["LOGIN"],
                    password=current_app.config["SMTP"].get("PASSWORD"),
                )
            smtp.send_message(msg)

    except smtplib.SMTPRecipientsRefused:
        pass

    except OSError as exc:
        logging.exception(f"Could not send email: {exc}")
        return False

    return True
