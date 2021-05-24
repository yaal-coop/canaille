import hashlib
from flask import url_for, render_template, current_app
from flask_babel import gettext as _
from .apputils import logo, send_email


def profile_hash(user, password):
    return hashlib.sha256(
        current_app.config["SECRET_KEY"].encode("utf-8")
        + user.encode("utf-8")
        + password.encode("utf-8")
    ).hexdigest()


def send_password_reset_mail(user):
    base_url = url_for("account.index", _external=True)
    reset_url = url_for(
        "account.reset",
        uid=user.uid[0],
        hash=profile_hash(
            user.uid[0], user.userPassword[0] if user.has_password() else ""
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
        logo="cid:{}".format(logo_cid[1:-1]) if logo_cid else None,
    )

    return send_email(
        subject=subject,
        recipient=user.mail,
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
            user.uid[0], user.userPassword[0] if user.has_password() else ""
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
        logo="cid:{}".format(logo_cid[1:-1]) if logo_cid else None,
    )

    return send_email(
        subject=subject,
        recipient=user.mail,
        text=text_body,
        html=html_body,
        attachements=[(logo_cid, logo_filename, logo_raw)] if logo_filename else None,
    )
