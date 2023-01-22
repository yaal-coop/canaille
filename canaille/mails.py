import email.message
import mimetypes
import smtplib
import urllib.request
from email.utils import make_msgid

from flask import current_app
from flask import request
from flask import url_for
from flask_babel import gettext as _
from flask_themer import render_template

from .apputils import get_current_domain
from .apputils import get_current_mail_domain
from .apputils import profile_hash

DEFAULT_SMTP_HOST = "localhost"
DEFAULT_SMTP_PORT = 25
DEFAULT_SMTP_TLS = False


def logo():
    logo_url = current_app.config.get("LOGO")
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


def send_email(subject, recipient, text, html, attachements=None):
    current_app.logger.debug(f"Sending a mail to {recipient}: {subject}")
    msg = email.message.EmailMessage()
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    msg["Subject"] = subject
    msg["To"] = f"<{recipient}>"

    name = current_app.config.get("NAME", "Canaille")
    address = current_app.config["SMTP"].get("FROM_ADDR")

    if not address:
        domain = get_current_mail_domain()
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
        current_app.logger.warning(f"Could not send email: {exc}")
        return False

    return True


def send_test_mail(email):
    base_url = url_for("account.index", _external=True)
    logo_cid, logo_filename, logo_raw = logo()

    subject = _("Test email from {website_name}").format(
        website_name=current_app.config.get("NAME", "Canaille")
    )
    text_body = render_template(
        "mail/test.txt",
        site_name=current_app.config.get("NAME", "Canaille"),
        site_url=base_url,
    )
    html_body = render_template(
        "mail/test.html",
        site_name=current_app.config.get("NAME", "Canaille"),
        site_url=base_url,
        logo=f"cid:{logo_cid[1:-1]}" if logo_cid else None,
    )

    return send_email(
        subject=subject,
        recipient=email,
        text=text_body,
        html=html_body,
        attachements=[(logo_cid, logo_filename, logo_raw)] if logo_filename else None,
    )


def send_password_reset_mail(user):
    base_url = url_for("account.index", _external=True)
    reset_url = url_for(
        "account.reset",
        uid=user.uid[0],
        hash=profile_hash(
            user.uid[0],
            user.mail[0],
            user.userPassword[0] if user.has_password() else "",
        ),
        _external=True,
    )
    logo_cid, logo_filename, logo_raw = logo()

    subject = _("Password reset on {website_name}").format(
        website_name=current_app.config.get("NAME", reset_url)
    )
    text_body = render_template(
        "mail/reset.txt",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=base_url,
        reset_url=reset_url,
    )
    html_body = render_template(
        "mail/reset.html",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=base_url,
        reset_url=reset_url,
        logo=f"cid:{logo_cid[1:-1]}" if logo_cid else None,
    )

    return send_email(
        subject=subject,
        recipient=user.mail[0],
        text=text_body,
        html=html_body,
        attachements=[(logo_cid, logo_filename, logo_raw)] if logo_filename else None,
    )


def send_password_initialization_mail(user):
    base_url = url_for("account.index", _external=True)
    reset_url = url_for(
        "account.reset",
        uid=user.uid[0],
        hash=profile_hash(
            user.uid[0],
            user.mail[0],
            user.userPassword[0] if user.has_password() else "",
        ),
        _external=True,
    )
    logo_cid, logo_filename, logo_raw = logo()

    subject = _("Password initialization on {website_name}").format(
        website_name=current_app.config.get("NAME", reset_url)
    )
    text_body = render_template(
        "mail/firstlogin.txt",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=base_url,
        reset_url=reset_url,
    )
    html_body = render_template(
        "mail/firstlogin.html",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=base_url,
        reset_url=reset_url,
        logo=f"cid:{logo_cid[1:-1]}" if logo_cid else None,
    )

    return send_email(
        subject=subject,
        recipient=user.mail[0],
        text=text_body,
        html=html_body,
        attachements=[(logo_cid, logo_filename, logo_raw)] if logo_filename else None,
    )


def send_invitation_mail(email, registration_url):
    base_url = url_for("account.index", _external=True)
    logo_cid, logo_filename, logo_raw = logo()

    subject = _("You have been invited to create an account on {website_name}").format(
        website_name=current_app.config.get("NAME", registration_url)
    )
    text_body = render_template(
        "mail/invitation.txt",
        site_name=current_app.config.get("NAME", registration_url),
        site_url=base_url,
        registration_url=registration_url,
    )
    html_body = render_template(
        "mail/invitation.html",
        site_name=current_app.config.get("NAME", registration_url),
        site_url=base_url,
        registration_url=registration_url,
        logo=f"cid:{logo_cid[1:-1]}" if logo_cid else None,
    )

    return send_email(
        subject=subject,
        recipient=email,
        text=text_body,
        html=html_body,
        attachements=[(logo_cid, logo_filename, logo_raw)] if logo_filename else None,
    )
