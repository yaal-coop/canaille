import datetime
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_babel import gettext
from oidc_ldap_bridge.models import Consent, Client
from oidc_ldap_bridge.flaskutils import user_needed


bp = Blueprint(__name__, "consents")


@bp.route("/")
@user_needed()
def consents(user):
    consents = Consent.filter(oauthSubject=user.dn)
    consents = [c for c in consents if not c.oauthRevokationDate]
    client_dns = list(set(t.oauthClient for t in consents))
    clients = {dn: Client.get(dn) for dn in client_dns}
    return render_template("consent_list.html", consents=consents, clients=clients)


@bp.route("/delete/<consent_id>")
@user_needed()
def delete(user, consent_id):
    consent = Consent.get(consent_id)

    if not consent or consent.oauthSubject != user.dn:
        flash(gettext("Could not delete this access"), "error")

    else:
        consent.revoke()
        flash(gettext("The access has been revoked"), "success")

    return redirect(url_for("oidc_ldap_bridge.consents.consents"))
