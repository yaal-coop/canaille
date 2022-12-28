from canaille.flaskutils import user_needed
from canaille.oidc.models import Client
from canaille.oidc.models import Consent
from flask import Blueprint
from flask import flash
from flask import redirect
from flask import url_for
from flask_babel import gettext
from flask_themer import render_template

from .utils import SCOPE_DETAILS


bp = Blueprint("consents", __name__, url_prefix="/consent")


@bp.route("/")
@user_needed()
def consents(user):
    consents = Consent.filter(subject=user.dn)
    consents = [c for c in consents if not c.revokation_date]
    client_dns = list({t.client for t in consents})
    clients = {dn: Client.get(dn) for dn in client_dns}
    return render_template(
        "oidc/user/consent_list.html",
        consents=consents,
        clients=clients,
        menuitem="consents",
        scope_details=SCOPE_DETAILS,
        ignored_scopes=["openid"],
    )


@bp.route("/delete/<consent_id>")
@user_needed()
def delete(user, consent_id):
    consent = Consent.get(consent_id)

    if not consent or consent.subject != user.dn:
        flash(gettext("Could not delete this access"), "error")

    else:
        consent.revoke()
        flash(gettext("The access has been revoked"), "success")

    return redirect(url_for("oidc.consents.consents"))
