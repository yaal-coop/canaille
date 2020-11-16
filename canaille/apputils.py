import base64
import email.message
import logging
import smtplib
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


def send_email(subject, sender, recipient, text, html):
    msg = email.message.EmailMessage()
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

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

    except OSError:
        logging.exception("Could not send password reset email")
        return False

    return True
