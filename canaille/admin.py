from canaille.apputils import obj_to_b64
from canaille.flaskutils import permissions_needed
from canaille.mails import profile_hash
from canaille.mails import send_test_mail
from flask import Blueprint
from flask import current_app
from flask import flash
from flask import request
from flask import url_for
from flask_babel import gettext as _
from flask_themer import render_template
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired
from wtforms.validators import Email


bp = Blueprint("admin", __name__, url_prefix="/admin")


class MailTestForm(FlaskForm):
    mail = StringField(
        _("Email"),
        validators=[
            DataRequired(),
            Email(),
        ],
        render_kw={
            "placeholder": _("jane@doe.com"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    )


@bp.route("/mail", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def mail_index(user):
    form = MailTestForm(request.form or None)
    if request.form and form.validate():
        if send_test_mail(form.mail.data):
            flash(_("The test invitation mail has been sent correctly"), "success")
        else:
            flash(_("The test invitation mail has not been sent correctly"), "error")

    return render_template("mail/admin.html", form=form, menuitem="admin")


@bp.route("/mail/test.html")
@permissions_needed("manage_oidc")
def test_html(user):
    base_url = url_for("account.index", _external=True)
    return render_template(
        "mail/test.html",
        site_name=current_app.config.get("NAME", "Canaille"),
        site_url=base_url,
        logo=current_app.config.get("LOGO"),
    )


@bp.route("/mail/test.txt")
@permissions_needed("manage_oidc")
def test_txt(user):
    base_url = url_for("account.index", _external=True)
    return render_template(
        "mail/test.txt",
        site_name=current_app.config.get("NAME", "Canaille"),
        site_url=current_app.config.get("SERVER_NAME", base_url),
    )


@bp.route("/mail/password-init.html")
@permissions_needed("manage_oidc")
def password_init_html(user):
    base_url = url_for("account.index", _external=True)
    reset_url = url_for(
        "account.reset",
        uid=user.uid[0],
        hash=profile_hash(user.uid[0], user.mail[0], user.userPassword[0]),
        _external=True,
    )

    return render_template(
        "mail/firstlogin.html",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=base_url,
        reset_url=reset_url,
        logo=current_app.config.get("LOGO"),
        title=_("Password initialization on {website_name}").format(
            website_name=current_app.config.get("NAME", reset_url)
        ),
    )


@bp.route("/mail/password-init.txt")
@permissions_needed("manage_oidc")
def password_init_txt(user):
    base_url = url_for("account.index", _external=True)
    reset_url = url_for(
        "account.reset",
        uid=user.uid[0],
        hash=profile_hash(user.uid[0], user.mail[0], user.userPassword[0]),
        _external=True,
    )

    return render_template(
        "mail/firstlogin.txt",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=current_app.config.get("SERVER_NAME", base_url),
        reset_url=reset_url,
    )


@bp.route("/mail/reset.html")
@permissions_needed("manage_oidc")
def password_reset_html(user):
    base_url = url_for("account.index", _external=True)
    reset_url = url_for(
        "account.reset",
        uid=user.uid[0],
        hash=profile_hash(user.uid[0], user.mail[0], user.userPassword[0]),
        _external=True,
    )

    return render_template(
        "mail/reset.html",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=base_url,
        reset_url=reset_url,
        logo=current_app.config.get("LOGO"),
        title=_("Password reset on {website_name}").format(
            website_name=current_app.config.get("NAME", reset_url)
        ),
    )


@bp.route("/mail/reset.txt")
@permissions_needed("manage_oidc")
def password_reset_txt(user):
    base_url = url_for("account.index", _external=True)
    reset_url = url_for(
        "account.reset",
        uid=user.uid[0],
        hash=profile_hash(user.uid[0], user.mail[0], user.userPassword[0]),
        _external=True,
    )

    return render_template(
        "mail/reset.txt",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=current_app.config.get("SERVER_NAME", base_url),
        reset_url=reset_url,
    )


@bp.route("/mail/<uid>/<email>/invitation.html")
@permissions_needed("manage_oidc")
def invitation_html(user, uid, email):
    base_url = url_for("account.index", _external=True)
    registration_url = url_for(
        "account.registration",
        data=obj_to_b64([uid, email]),
        hash=profile_hash(uid, email),
        _external=True,
    )

    return render_template(
        "mail/invitation.html",
        site_name=current_app.config.get("NAME", base_url),
        site_url=base_url,
        registration_url=registration_url,
        logo=current_app.config.get("LOGO"),
        title=_("Invitation on {website_name}").format(
            website_name=current_app.config.get("NAME", base_url)
        ),
    )


@bp.route("/mail/<uid>/<email>/invitation.txt")
@permissions_needed("manage_oidc")
def invitation_txt(user, uid, email):
    base_url = url_for("account.index", _external=True)
    registration_url = url_for(
        "account.registration",
        data=obj_to_b64([uid, email]),
        hash=profile_hash(uid, email),
        _external=True,
    )

    return render_template(
        "mail/invitation.txt",
        site_name=current_app.config.get("NAME", base_url),
        site_url=base_url,
        registration_url=registration_url,
    )
