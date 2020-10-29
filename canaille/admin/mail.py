import base64
import urllib.request
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

    logo = None
    logo_extension = None
    if current_app.config.get("LOGO"):
        logo_extension = current_app.config["LOGO"].split(".")[-1]
        try:
            with urllib.request.urlopen(current_app.config.get("LOGO")) as f:
                logo = base64.b64encode(f.read()).decode("utf-8")
        except (urllib.error.HTTPError, urllib.error.URLError):
            pass

    return render_template(
        "mail/reset.html",
        site_name=current_app.config.get("NAME", reset_url),
        site_url=current_app.config.get("URL", base_url),
        reset_url=reset_url,
        logo=logo,
        logo_extension=logo_extension,
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
