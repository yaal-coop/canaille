from flask import Blueprint
from flask import current_app
from flask import flash
from flask import request
from flask import url_for
from wtforms import StringField
from wtforms.validators import DataRequired

from canaille.app import obj_to_b64
from canaille.app.flask import user_needed
from canaille.app.forms import Form
from canaille.app.forms import email_validator
from canaille.app.i18n import gettext as _
from canaille.app.templating import render_template
from canaille.core.mails import build_hash
from canaille.core.mails import send_test_mail

bp = Blueprint("admin", __name__, url_prefix="/admin")


class MailTestForm(Form):
    email = StringField(
        _("Email"),
        validators=[
            DataRequired(),
            email_validator,
        ],
        render_kw={
            "placeholder": _("jane.doe@example.com"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    )


@bp.route("/mail", methods=["GET", "POST"])
@user_needed("manage_oidc")
def mail_index(user):
    form = MailTestForm(request.form or None)
    if request.form and form.validate():
        if send_test_mail(form.email.data):
            flash(_("The test mail has been sent correctly"), "success")
        else:
            flash(_("The test mail has not been sent correctly"), "error")

    return render_template("core/mails/admin.html", form=form, menuitem="admin")


@bp.route("/mail/test.html")
@user_needed("manage_oidc")
def test_html(user):
    base_url = url_for("core.account.index", _external=True)
    return render_template(
        "core/mails/test.html",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=base_url,
        logo=current_app.config["CANAILLE"]["LOGO"],
        title=_("Test email from {website_name}").format(
            website_name=current_app.config["CANAILLE"]["NAME"],
        ),
    )


@bp.route("/mail/test.txt")
@user_needed("manage_oidc")
def test_txt(user):
    base_url = url_for("core.account.index", _external=True)
    return render_template(
        "core/mails/test.txt",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=current_app.config.get("SERVER_NAME", base_url),
    )


@bp.route("/mail/password-init.html")
@user_needed("manage_oidc")
def password_init_html(user):
    base_url = url_for("core.account.index", _external=True)
    reset_url = url_for(
        "core.auth.reset",
        user=user,
        hash=build_hash(user.identifier, user.preferred_email, user.password),
        title=_("Password initialization on {website_name}").format(
            website_name=current_app.config["CANAILLE"]["NAME"]
        ),
        _external=True,
    )

    return render_template(
        "core/mails/firstlogin.html",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=base_url,
        reset_url=reset_url,
        logo=current_app.config["CANAILLE"]["LOGO"],
        title=_("Password initialization on {website_name}").format(
            website_name=current_app.config["CANAILLE"]["NAME"]
        ),
    )


@bp.route("/mail/password-init.txt")
@user_needed("manage_oidc")
def password_init_txt(user):
    base_url = url_for("core.account.index", _external=True)
    reset_url = url_for(
        "core.auth.reset",
        user=user,
        hash=build_hash(user.identifier, user.preferred_email, user.password),
        _external=True,
    )

    return render_template(
        "core/mails/firstlogin.txt",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=current_app.config.get("SERVER_NAME", base_url),
        reset_url=reset_url,
    )


@bp.route("/mail/reset.html")
@user_needed("manage_oidc")
def password_reset_html(user):
    base_url = url_for("core.account.index", _external=True)
    reset_url = url_for(
        "core.auth.reset",
        user=user,
        hash=build_hash(user.identifier, user.preferred_email, user.password),
        title=_("Password reset on {website_name}").format(
            website_name=current_app.config["CANAILLE"]["NAME"]
        ),
        _external=True,
    )

    return render_template(
        "core/mails/reset.html",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=base_url,
        reset_url=reset_url,
        logo=current_app.config["CANAILLE"]["LOGO"],
        title=_("Password reset on {website_name}").format(
            website_name=current_app.config["CANAILLE"]["NAME"]
        ),
    )


@bp.route("/mail/reset.txt")
@user_needed("manage_oidc")
def password_reset_txt(user):
    base_url = url_for("core.account.index", _external=True)
    reset_url = url_for(
        "core.auth.reset",
        user=user,
        hash=build_hash(user.identifier, user.preferred_email, user.password),
        _external=True,
    )

    return render_template(
        "core/mails/reset.txt",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=current_app.config.get("SERVER_NAME", base_url),
        reset_url=reset_url,
    )


@bp.route("/mail/<identifier>/<email>/invitation.html")
@user_needed("manage_oidc")
def invitation_html(user, identifier, email):
    base_url = url_for("core.account.index", _external=True)
    registration_url = url_for(
        "core.account.registration",
        data=obj_to_b64([identifier, email]),
        hash=build_hash(identifier, email),
        _external=True,
    )

    return render_template(
        "core/mails/invitation.html",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=base_url,
        registration_url=registration_url,
        logo=current_app.config["CANAILLE"]["LOGO"],
        title=_("Invitation on {website_name}").format(
            website_name=current_app.config["CANAILLE"]["NAME"]
        ),
    )


@bp.route("/mail/<identifier>/<email>/invitation.txt")
@user_needed("manage_oidc")
def invitation_txt(user, identifier, email):
    base_url = url_for("core.account.index", _external=True)
    registration_url = url_for(
        "core.account.registration",
        data=obj_to_b64([identifier, email]),
        hash=build_hash(identifier, email),
        _external=True,
    )

    return render_template(
        "core/mails/invitation.txt",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=base_url,
        registration_url=registration_url,
    )


@bp.route("/mail/<identifier>/<email>/email-confirmation.html")
@user_needed("manage_oidc")
def email_confirmation_html(user, identifier, email):
    base_url = url_for("core.account.index", _external=True)
    email_confirmation_url = url_for(
        "core.account.email_confirmation",
        data=obj_to_b64([identifier, email]),
        hash=build_hash(identifier, email),
        _external=True,
    )

    return render_template(
        "core/mails/email-confirmation.html",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=base_url,
        confirmation_url=email_confirmation_url,
        logo=current_app.config["CANAILLE"]["LOGO"],
        title=_("Email confirmation on {website_name}").format(
            website_name=current_app.config["CANAILLE"]["NAME"]
        ),
    )


@bp.route("/mail/<identifier>/<email>/email-confirmation.txt")
@user_needed("manage_oidc")
def email_confirmation_txt(user, identifier, email):
    base_url = url_for("core.account.index", _external=True)
    email_confirmation_url = url_for(
        "core.account.email_confirmation",
        data=obj_to_b64([identifier, email]),
        hash=build_hash(identifier, email),
        _external=True,
    )

    return render_template(
        "core/mails/email-confirmation.txt",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=base_url,
        confirmation_url=email_confirmation_url,
    )


@bp.route("/mail/<email>/registration.html")
@user_needed("manage_oidc")
def registration_html(user, email):
    base_url = url_for("core.account.index", _external=True)
    registration_url = url_for(
        "core.account.registration",
        data=obj_to_b64([email]),
        hash=build_hash(email),
        _external=True,
    )

    return render_template(
        "core/mails/registration.html",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=base_url,
        registration_url=registration_url,
        logo=current_app.config["CANAILLE"]["LOGO"],
        title=_("Email confirmation on {website_name}").format(
            website_name=current_app.config["CANAILLE"]["NAME"]
        ),
    )


@bp.route("/mail/<email>/registration.txt")
@user_needed("manage_oidc")
def registration_txt(user, email):
    base_url = url_for("core.account.index", _external=True)
    registration_url = url_for(
        "core.account.registration",
        data=obj_to_b64([email]),
        hash=build_hash(email),
        _external=True,
    )

    return render_template(
        "core/mails/registration.txt",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=base_url,
        registration_url=registration_url,
    )


@bp.route("/mail/compromised_password_check_failure.html")
@user_needed("manage_oidc")
def compromised_password_check_failure_html(user):
    base_url = url_for("core.account.index", _external=True)
    user_name = "<USER NAME>"
    check_password_url = "<URL TO CHECK PASSWORD>"
    hashed_password = "<HASHED PASSWORD>"
    user_email = "<USER EMAIL>"

    return render_template(
        "core/mails/compromised_password_check_failure.html",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=base_url,
        user_name=user_name,
        check_password_url=check_password_url,
        hashed_password=hashed_password,
        logo=current_app.config["CANAILLE"]["LOGO"],
        user_email=user_email,
        title=_("Compromised password check failure on {website_name}").format(
            website_name=current_app.config["CANAILLE"]["NAME"]
        ),
    )


@bp.route("/mail/compromised_password_check_failure.txt")
@user_needed("manage_oidc")
def compromised_password_check_failure_txt(user):
    base_url = url_for("core.account.index", _external=True)
    user_name = "<USER NAME>"
    check_password_url = "<URL TO CHECK PASSWORD>"
    hashed_password = "<HASHED PASSWORD>"
    user_email = "<USER EMAIL>"

    return render_template(
        "core/mails/compromised_password_check_failure.txt",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=base_url,
        user_name=user_name,
        check_password_url=check_password_url,
        hashed_password=hashed_password,
        user_email=user_email,
    )


@bp.route("/mail/email_otp.html")
@user_needed("manage_oidc")
def email_otp_html(user):
    base_url = url_for("core.account.index", _external=True)
    otp = "000000"

    return render_template(
        "core/mails/email_otp.html",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=base_url,
        otp=otp,
        logo=current_app.config["CANAILLE"]["LOGO"],
        title=_("One-time password authentication on {website_name}").format(
            website_name=current_app.config["CANAILLE"]["NAME"]
        ),
    )


@bp.route("/mail/email_otp.txt")
@user_needed("manage_oidc")
def email_otp_txt(user):
    base_url = url_for("core.account.index", _external=True)
    otp = "000000"

    return render_template(
        "core/mails/email_otp.txt",
        site_name=current_app.config["CANAILLE"]["NAME"],
        site_url=base_url,
        otp=otp,
    )
