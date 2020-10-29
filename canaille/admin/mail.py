from flask import Blueprint, render_template, current_app, request, url_for
from canaille.flaskutils import admin_needed
from canaille.account import profile_hash


bp = Blueprint(__name__, "clients")


@bp.route("/reset.html")
@admin_needed()
def reset_html(user):
    base_url = current_app.config.get("URL") or request.url_root
    reset_url = base_url + url_for(
        "canaille.account.reset",
        uid=user.uid[0],
        hash=profile_hash(user.uid[0], user.userPassword[0]),
    )[1:]

    return render_template(
        "mail/reset.html",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=current_app.config.get("URL", base_url),
        reset_url=reset_url,
        logo=current_app.config.get("LOGO"),
    )


@bp.route("/reset.txt")
@admin_needed()
def reset_txt(user):
    base_url = current_app.config.get("URL") or request.url_root
    reset_url = base_url + url_for(
        "canaille.account.reset",
        uid=user.uid[0],
        hash=profile_hash(user.uid[0], user.userPassword[0]),
    )[1:]

    return render_template(
        "mail/reset.txt",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=current_app.config.get("URL", base_url),
        reset_url=reset_url,
    )
