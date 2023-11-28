from canaille.app import build_hash
from canaille.app.i18n import gettext as _
from canaille.app.mails import logo
from canaille.app.mails import send_email
from canaille.app.themes import render_template
from flask import current_app
from flask import url_for


def send_test_mail(email):
    base_url = url_for("core.account.index", _external=True)
    logo_cid, logo_filename, logo_raw = logo()

    subject = _("Test email from {website_name}").format(
        website_name=current_app.config.get("NAME", "Canaille")
    )
    text_body = render_template(
        "mails/test.txt",
        site_name=current_app.config.get("NAME", "Canaille"),
        site_url=base_url,
    )
    html_body = render_template(
        "mails/test.html",
        site_name=current_app.config.get("NAME", "Canaille"),
        site_url=base_url,
        logo=f"cid:{logo_cid[1:-1]}" if logo_cid else None,
        title=subject,
    )

    return send_email(
        subject=subject,
        recipient=email,
        text=text_body,
        html=html_body,
        attachements=[(logo_cid, logo_filename, logo_raw)] if logo_filename else None,
    )


def send_password_reset_mail(user, mail):
    base_url = url_for("core.account.index", _external=True)
    reset_url = url_for(
        "core.auth.reset",
        user=user,
        hash=build_hash(
            user.identifier,
            mail,
            user.password if user.has_password() else "",
        ),
        _external=True,
    )
    logo_cid, logo_filename, logo_raw = logo()

    subject = _("Password reset on {website_name}").format(
        website_name=current_app.config.get("NAME", base_url)
    )
    text_body = render_template(
        "mails/reset.txt",
        site_name=current_app.config.get("NAME", base_url),
        site_url=base_url,
        reset_url=reset_url,
    )
    html_body = render_template(
        "mails/reset.html",
        site_name=current_app.config.get("NAME", base_url),
        site_url=base_url,
        reset_url=reset_url,
        logo=f"cid:{logo_cid[1:-1]}" if logo_cid else None,
        title=subject,
    )

    return send_email(
        subject=subject,
        recipient=mail,
        text=text_body,
        html=html_body,
        attachements=[(logo_cid, logo_filename, logo_raw)] if logo_filename else None,
    )


def send_password_initialization_mail(user, email):
    base_url = url_for("core.account.index", _external=True)
    reset_url = url_for(
        "core.auth.reset",
        user=user,
        hash=build_hash(
            user.identifier,
            email,
            user.password if user.has_password() else "",
        ),
        _external=True,
    )
    logo_cid, logo_filename, logo_raw = logo()

    subject = _("Password initialization on {website_name}").format(
        website_name=current_app.config.get("NAME", base_url)
    )
    text_body = render_template(
        "mails/firstlogin.txt",
        site_name=current_app.config.get("NAME", base_url),
        site_url=base_url,
        reset_url=reset_url,
    )
    html_body = render_template(
        "mails/firstlogin.html",
        site_name=current_app.config.get("NAME", base_url),
        site_url=base_url,
        reset_url=reset_url,
        logo=f"cid:{logo_cid[1:-1]}" if logo_cid else None,
        title=subject,
    )

    return send_email(
        subject=subject,
        recipient=email,
        text=text_body,
        html=html_body,
        attachements=[(logo_cid, logo_filename, logo_raw)] if logo_filename else None,
    )


def send_invitation_mail(email, registration_url):
    base_url = url_for("core.account.index", _external=True)
    logo_cid, logo_filename, logo_raw = logo()

    subject = _("You have been invited to create an account on {website_name}").format(
        website_name=current_app.config.get("NAME", base_url)
    )
    text_body = render_template(
        "mails/invitation.txt",
        site_name=current_app.config.get("NAME", base_url),
        site_url=base_url,
        registration_url=registration_url,
    )
    html_body = render_template(
        "mails/invitation.html",
        site_name=current_app.config.get("NAME", base_url),
        site_url=base_url,
        registration_url=registration_url,
        logo=f"cid:{logo_cid[1:-1]}" if logo_cid else None,
        title=subject,
    )

    return send_email(
        subject=subject,
        recipient=email,
        text=text_body,
        html=html_body,
        attachements=[(logo_cid, logo_filename, logo_raw)] if logo_filename else None,
    )


def send_confirmation_email(email, confirmation_url):
    base_url = url_for("core.account.index", _external=True)
    logo_cid, logo_filename, logo_raw = logo()

    subject = _("Confirm your address email on {website_name}").format(
        website_name=current_app.config.get("NAME", base_url)
    )
    text_body = render_template(
        "mails/email-confirmation.txt",
        site_name=current_app.config.get("NAME", base_url),
        site_url=base_url,
        confirmation_url=confirmation_url,
    )
    html_body = render_template(
        "mails/email-confirmation.html",
        site_name=current_app.config.get("NAME", base_url),
        site_url=base_url,
        confirmation_url=confirmation_url,
        logo=f"cid:{logo_cid[1:-1]}" if logo_cid else None,
        title=subject,
    )

    return send_email(
        subject=subject,
        recipient=email,
        text=text_body,
        html=html_body,
        attachements=[(logo_cid, logo_filename, logo_raw)] if logo_filename else None,
    )


def send_registration_mail(email, registration_url):
    base_url = url_for("core.account.index", _external=True)
    logo_cid, logo_filename, logo_raw = logo()

    subject = _("Continue your registration on {website_name}").format(
        website_name=current_app.config.get("NAME", registration_url)
    )
    text_body = render_template(
        "mails/registration.txt",
        site_name=current_app.config.get("NAME", base_url),
        site_url=base_url,
        registration_url=registration_url,
    )
    html_body = render_template(
        "mails/registration.html",
        site_name=current_app.config.get("NAME", base_url),
        site_url=base_url,
        registration_url=registration_url,
        logo=f"cid:{logo_cid[1:-1]}" if logo_cid else None,
        title=subject,
    )

    return send_email(
        subject=subject,
        recipient=email,
        text=text_body,
        html=html_body,
        attachements=[(logo_cid, logo_filename, logo_raw)] if logo_filename else None,
    )
