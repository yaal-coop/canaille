import datetime
import uuid

from flask import Blueprint
from flask import current_app
from flask import flash
from flask import redirect
from flask import url_for

from canaille.app import models
from canaille.app.flask import user_needed
from canaille.app.i18n import gettext as _
from canaille.app.templating import render_template
from canaille.backends import Backend

from ..utils import SCOPE_DETAILS

bp = Blueprint("consents", __name__, url_prefix="/consent")


@bp.route("/")
@user_needed()
def consents(user):
    consents = Backend.instance.query(models.Consent, subject=user)
    clients = {t.client for t in consents}

    nb_consents = len(consents)
    nb_trusted = sum(
        1
        for client in Backend.instance.query(models.Client)
        if client.trusted and client not in clients
    )

    return render_template(
        "oidc/consent_list.html",
        consents=consents,
        menuitem="consents",
        scope_details=SCOPE_DETAILS,
        ignored_scopes=["openid"],
        nb_consents=nb_consents,
        nb_trusted=nb_trusted,
    )


@bp.route("/trusted-applications")
@user_needed()
def pre_consents(user):
    consents = Backend.instance.query(models.Consent, subject=user)
    clients = {t.client for t in consents}
    trusted = [
        client
        for client in Backend.instance.query(models.Client)
        if client.trusted and client not in clients
    ]

    nb_consents = len(consents)
    nb_trusted = len(trusted)

    return render_template(
        "oidc/trusted_list.html",
        menuitem="consents",
        scope_details=SCOPE_DETAILS,
        # TODO: do not delegate this var to the templates, or set this explicitly in the templates.
        ignored_scopes=["openid"],
        trusted=trusted,
        nb_consents=nb_consents,
        nb_trusted=nb_trusted,
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
        current_app.logger.security(
            f"Consent revoked for {user.user_name} in client {consent.client.client_name}"
        )
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
        Backend.instance.save(consent)
        flash(_("The access has been restored"), "success")

    return redirect(url_for("oidc.consents.consents"))


@bp.route("/revoke-trusted/<client(required=False):client>")
@user_needed()
def revoke_trusted(user, client):
    if not client or not client.trusted:
        flash(_("Could not revoke this access"), "error")
        return redirect(url_for("oidc.consents.consents"))

    consent = Backend.instance.get(models.Consent, client=client, subject=user)
    if consent:
        return redirect(url_for("oidc.consents.revoke", consent=consent))

    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=user,
        scope=client.scope,
    )
    consent.revoke()
    Backend.instance.save(consent)
    flash(_("The access has been revoked"), "success")

    return redirect(url_for("oidc.consents.consents"))
