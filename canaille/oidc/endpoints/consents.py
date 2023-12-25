import datetime
import uuid

from canaille.app import models
from canaille.app.flask import user_needed
from canaille.app.i18n import gettext as _
from canaille.app.themes import render_template
from flask import Blueprint
from flask import flash
from flask import redirect
from flask import url_for

from ..utils import SCOPE_DETAILS


bp = Blueprint("consents", __name__, url_prefix="/consent")


@bp.route("/")
@user_needed()
def consents(user):
    consents = models.Consent.query(subject=user)
    clients = {t.client for t in consents}

    nb_consents = len(consents)
    nb_preconsents = sum(
        1
        for client in models.Client.query()
        if client.preconsent and client not in clients
    )

    return render_template(
        "consent_list.html",
        consents=consents,
        menuitem="consents",
        scope_details=SCOPE_DETAILS,
        ignored_scopes=["openid"],
        nb_consents=nb_consents,
        nb_preconsents=nb_preconsents,
    )


@bp.route("/pre-consents")
@user_needed()
def pre_consents(user):
    consents = models.Consent.query(subject=user)
    clients = {t.client for t in consents}
    preconsented = [
        client
        for client in models.Client.query()
        if client.preconsent and client not in clients
    ]

    nb_consents = len(consents)
    nb_preconsents = len(preconsented)

    return render_template(
        "preconsent_list.html",
        menuitem="consents",
        scope_details=SCOPE_DETAILS,
        ignored_scopes=["openid"],
        preconsented=preconsented,
        nb_consents=nb_consents,
        nb_preconsents=nb_preconsents,
    )


@bp.route("/revoke/<consent(required=False):consent>")
@user_needed()
def revoke(user, consent):
    if not consent or consent.subject != user:
        flash(_("Could not revoke this access"), "error")

    elif consent.revokation_date:
        flash(_("The access is already revoked"), "error")

    else:
        consent.revoke()
        flash(_("The access has been revoked"), "success")

    return redirect(url_for("oidc.consents.consents"))


@bp.route("/restore/<consent(required=False):consent>")
@user_needed()
def restore(user, consent):
    if not consent or consent.subject != user:
        flash(_("Could not restore this access"), "error")

    elif not consent.revokation_date:
        flash(_("The access is not revoked"), "error")

    else:
        consent.restore()
        if not consent.issue_date:
            consent.issue_date = datetime.datetime.now(datetime.timezone.utc)
        consent.save()
        flash(_("The access has been restored"), "success")

    return redirect(url_for("oidc.consents.consents"))


@bp.route("/revoke-preconsent/<client(required=False):client>")
@user_needed()
def revoke_preconsent(user, client):
    if not client or not client.preconsent:
        flash(_("Could not revoke this access"), "error")
        return redirect(url_for("oidc.consents.consents"))

    consent = models.Consent.get(client=client, subject=user)
    if consent:
        return redirect(url_for("oidc.consents.revoke", consent=consent))

    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=user,
        scope=client.scope,
    )
    consent.revoke()
    consent.save()
    flash(_("The access has been revoked"), "success")

    return redirect(url_for("oidc.consents.consents"))
