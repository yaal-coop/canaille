from flask import Blueprint

from canaille.app.flask import user_needed
from canaille.app.templating import render_template

bp = Blueprint("rotate", __name__, url_prefix="/admin/rotate")


@bp.route("/", methods=["GET", "POST"])
@user_needed("manage_oidc")
def index(user):
    # afficher des infos sur la clé actuelle (depuis quand elle est là par ex.)
    # afficher un formulaire avec un bouton rotate key
    return render_template(
        "oidc/key_rotation.html",
    )
