import email.message
import mimetypes
import smtplib
import urllib.request
from email.utils import make_msgid

from flask import current_app
from flask import request

from canaille.app import get_current_domain
from canaille.app import get_current_mail_domain


def logo():
    logo_url = current_app.config["CANAILLE"]["LOGO"]
    if not logo_url:
        return None, None, None

    logo_filename = logo_url.split("/")[-1]
    if not logo_url.startswith("http"):
        if current_app.config.get("SERVER_NAME"):
            logo_url = "{}://{}/{}".format(
                current_app.config.get("PREFERRED_URL_SCHEME"),
                get_current_domain(),
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

    logo_cid = make_msgid(domain=get_current_mail_domain())
    return logo_cid, logo_filename, logo_raw


def type_from_filename(filename):
    filetype = mimetypes.guess_type(filename)
    if not filetype or not filetype[0]:
        # For some reasons GHA fails to guess webp mimetypes
        # According to MDN, the default mimetype should be application/octet-stream
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
        return "application", "octet-stream"

    maintype, subtype = filetype[0].split("/")
    return maintype, subtype


def send_email(subject, recipient, text, html, attachments=None):
    current_app.logger.debug(f"Sending a mail to {recipient}: {subject}")
    msg = email.message.EmailMessage()
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    msg["Subject"] = subject
    msg["To"] = f"<{recipient}>"

    name = current_app.config["CANAILLE"]["NAME"]
    address = current_app.config["CANAILLE"]["SMTP"]["FROM_ADDR"]

    if not address:
        domain = get_current_mail_domain()
        address = f"admin@{domain}"

    msg["From"] = f'"{name}" <{address}>'

    attachments = attachments or []
    for cid, filename, value in attachments:
        maintype, subtype = type_from_filename(filename)
        msg.get_payload()[1].add_related(
            value, maintype=maintype, subtype=subtype, cid=cid
        )

    smtp = None
    try:
        connection_func = (
            smtplib.SMTP_SSL
            if current_app.config["CANAILLE"]["SMTP"]["SSL"]
            else smtplib.SMTP
        )
        with connection_func(
            host=current_app.config["CANAILLE"]["SMTP"]["HOST"],
            port=current_app.config["CANAILLE"]["SMTP"]["PORT"],
        ) as smtp:
            if current_app.config["CANAILLE"]["SMTP"]["TLS"]:
                smtp.starttls()
            if current_app.config["CANAILLE"]["SMTP"]["LOGIN"]:
                smtp.login(
                    user=current_app.config["CANAILLE"]["SMTP"]["LOGIN"],
                    password=current_app.config["CANAILLE"]["SMTP"]["PASSWORD"],
                )
            smtp.send_message(msg)

    except smtplib.SMTPRecipientsRefused:
        pass

    except OSError as exc:
        current_app.logger.warning(f"Could not send email: {exc}")
        return False

    return True
