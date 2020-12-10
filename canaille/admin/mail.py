import base64
import urllib.request
from flask import Blueprint, render_template, current_app, url_for, request
from flask_babel import gettext as _
from canaille.flaskutils import admin_needed
from canaille.account import profile_hash


bp = Blueprint(__name__, "clients")


@bp.route("/reset.html")
@admin_needed()
def reset_html(user):
    base_url = url_for("canaille.account.index", _external=True)
    reset_url = url_for(
        "canaille.account.reset",
        uid=user.uid[0],
        hash=profile_hash(user.uid[0], user.userPassword[0]),
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
    base_url = url_for("canaille.account.index", _external=True)
    reset_url = url_for(
        "canaille.account.reset",
        uid=user.uid[0],
        hash=profile_hash(user.uid[0], user.userPassword[0]),
        _external=True,
    )

    return render_template(
        "mail/reset.txt",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=current_app.config.get("SERVER_NAME", base_url),
        reset_url=reset_url,
    )
