from flask import Blueprint
from flask import current_app

from canaille.app.flask import user_needed
from canaille.app.templating import render_template
from canaille.oidc.installation import generate_keypair

bp = Blueprint("rotate", __name__, url_prefix="/admin/rotate")


@bp.route("/", methods=["GET", "POST"])
@user_needed("manage_oidc")
def index(user):
    # afficher des infos sur la clé actuelle (depuis quand elle est là par ex.)
    # afficher un formulaire avec un bouton rotate key
    return render_template(
        "oidc/key_rotation.html",
    )


@bp.route("/rotate-keys", methods=["GET", "POST"])
@user_needed("manage_oidc")
def rotate_keys(user):
    conf_keys = current_app.config["CANAILLE_OIDC"]["JWT"]
    conf_keys["OLD_PRIVATE_KEY"] = conf_keys["PRIVATE_KEY"]
    conf_keys["OLD_PUBLIC_KEY"] = conf_keys["PUBLIC_KEY"]
    private_key, public_key = generate_keypair()
    conf_keys["PUBLIC_KEY"] = public_key.decode()
    conf_keys["PRIVATE_KEY"] = private_key.decode()
    print(conf_keys["OLD_PRIVATE_KEY"])
    print(conf_keys["PRIVATE_KEY"])
    print(conf_keys["OLD_PUBLIC_KEY"])
    print(conf_keys["PUBLIC_KEY"])

    return render_template(
        "oidc/key_rotation.html",
    )
