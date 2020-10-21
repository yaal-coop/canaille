import datetime
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_babel import gettext
from canaille.models import Token, Client
from canaille.flaskutils import user_needed


bp = Blueprint(__name__, "tokens")


@bp.route("/")
@user_needed()
def tokens(user):
    tokens = Token.filter(oauthSubject=user.dn)
    tokens = [t for t in tokens if t.is_refresh_token_active()]
    client_dns = list(set(t.oauthClient for t in tokens))
    clients = {dn: Client.get(dn) for dn in client_dns}
    return render_template(
        "token_list.html", tokens=tokens, clients=clients, menuitem="tokens"
    )


@bp.route("/delete/<token_id>")
@user_needed()
def delete(user, token_id):
    token = Token.get(token_id)

    if not token or token.oauthSubject != user.dn:
        flash(gettext("Could not delete this access"), "error")

    else:
        token.oauthRevokationDate = datetime.datetime.now().strftime("%Y%m%d%H%M%SZ")
        token.save()
        flash(gettext("The access has been revoked"), "success")

    return redirect(url_for("canaille.tokens.tokens"))
