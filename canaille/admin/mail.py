from flask import Blueprint, current_app, url_for
from flask_themer import render_template
from flask_babel import gettext as _
from canaille.flaskutils import admin_needed
from canaille.mails import profile_hash
from canaille.apputils import obj_to_b64


bp = Blueprint("admin_mails", __name__)


@bp.route("/reset.html")
@admin_needed()
def reset_html(user):
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


@bp.route("/reset.txt")
@admin_needed()
def reset_txt(user):
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


@bp.route("/<uid>/<email>/invitation.html")
@admin_needed()
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


@bp.route("/<uid>/<email>/invitation.txt")
@admin_needed()
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
