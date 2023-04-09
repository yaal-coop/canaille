from canaille.app import profile_hash
from canaille.app.mails import logo
from canaille.app.mails import send_email
from flask import current_app
from flask import url_for
from flask_babel import gettext as _
from flask_themer import render_template


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
        user_name=user.user_name[0],
        hash=profile_hash(
            user.user_name[0],
            user.email[0],
            user.password[0] if user.has_password() else "",
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
        recipient=user.email[0],
        text=text_body,
        html=html_body,
        attachements=[(logo_cid, logo_filename, logo_raw)] if logo_filename else None,
    )


def send_password_initialization_mail(user):
    base_url = url_for("account.index", _external=True)
    reset_url = url_for(
        "account.reset",
        user_name=user.user_name[0],
        hash=profile_hash(
            user.user_name[0],
            user.email[0],
            user.password[0] if user.has_password() else "",
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
        recipient=user.email[0],
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
