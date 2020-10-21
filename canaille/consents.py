from flask import Blueprint, render_template, flash, redirect, url_for
from flask_babel import gettext
from canaille.models import Consent, Client
from canaille.flaskutils import user_needed


bp = Blueprint(__name__, "consents")


@bp.route("/")
@user_needed()
def consents(user):
    consents = Consent.filter(oauthSubject=user.dn)
    consents = [c for c in consents if not c.oauthRevokationDate]
    client_dns = list(set(t.oauthClient for t in consents))
    clients = {dn: Client.get(dn) for dn in client_dns}
    return render_template(
        "consent_list.html", consents=consents, clients=clients, menuitem="consents"
    )


@bp.route("/delete/<consent_id>")
@user_needed()
def delete(user, consent_id):
    consent = Consent.get(consent_id)

    if not consent or consent.oauthSubject != user.dn:
        flash(gettext("Could not delete this access"), "error")

    else:
        consent.revoke()
        flash(gettext("The access has been revoked"), "success")

    return redirect(url_for("canaille.consents.consents"))
