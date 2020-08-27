from flask import Blueprint, render_template, flash, redirect, url_for
from flask_babel import gettext
from web.models import Token, Client
from web.flaskutils import user_needed


bp = Blueprint(__name__, "tokens")


@bp.route("/")
@user_needed()
def tokens(user):
    tokens = Token.filter(oauthSubject=user.dn)
    tokens = [t for t in tokens if t.is_refresh_token_active()]
    client_ids = list(set(t.oauthClientID for t in tokens))
    clients = (
        {c.oauthClientID: c for c in Client.filter(oauthClientID=client_ids)}
        if client_ids
        else {}
    )
    return render_template("token_list.html", tokens=tokens, clients=clients)


@bp.route("/delete/<token_id>")
@user_needed()
def delete(user, token_id):
    token = Token.get(token_id)

    if not token or token.oauthSubject != user.dn:
        flash(gettext("Could not delete this access"), "error")

    else:
        token.revoked = True
        token.save()
        flash(gettext("The access has been revoked"), "success")

    return redirect(url_for("web.tokens.tokens"))
