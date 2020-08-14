import datetime
from flask import Blueprint, request, session, url_for
from flask import render_template, redirect, jsonify
from werkzeug.security import gen_salt
from authlib.integrations.flask_oauth2 import current_token
from authlib.oauth2 import OAuth2Error
from .models import User, Client
from .oauth2 import authorization, require_oauth


bp = Blueprint(__name__, 'home')


def current_user():
    if 'user_dn' in session:
        return User.get(session['user_dn'])
    return None


def split_by_crlf(s):
    return [v for v in s.splitlines() if v]


@bp.route('/', methods=('GET', 'POST'))
def home():
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.filter(cn=username)
        if not user:
            user = User(cn=username, sn=username)
            user.save()
        else:
            user = user[0]
        session["user_dn"] = user.dn
        return redirect('/')

    user = current_user()
    clients = Client.filter()
    return render_template('home.html', user=user, clients=clients)


@bp.route('/logout')
def logout():
    del session['id']
    return redirect('/')


@bp.route('/create_client', methods=('GET', 'POST'))
def create_client():
    user = current_user()
    if not user:
        return redirect('/')
    if request.method == 'GET':
        return render_template('create_client.html')

    form = request.form
    client_id = gen_salt(24)
    client_id_issued_at = datetime.datetime.now().strftime("%Y%m%d%H%M%SZ")
    client = Client(
        oauthClientID=client_id,
        oauthClientIDIssueTime=client_id_issued_at,
        oauthClientName=form["client_name"],
        oauthClientURI=form["client_uri"],
        oauthGrantType=split_by_crlf(form["grant_type"]),
        oauthRedirectURI=split_by_crlf(form["redirect_uri"]),
        oauthResponseType=split_by_crlf(form["response_type"]),
        oauthScopeValue=form["scope"],
        oauthTokenEndpointAuthMethod=form["token_endpoint_auth_method"]
    )

    if form['token_endpoint_auth_method'] == 'none':
        client.oauthClientSecret = ''
    else:
        client.oauthClientSecret = gen_salt(48)

    client.save()

    #db.session.add(client)
    #db.session.commit()
    return redirect('/')


@bp.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    user = current_user()
    # if user log status is not true (Auth server), then to log it in
    if not user:
        return redirect(url_for('website.routes.home', next=request.url))
    if request.method == 'GET':
        try:
            grant = authorization.validate_consent_request(end_user=user)
        except OAuth2Error as error:
            return error.error
        return render_template('authorize.html', user=user, grant=grant)
    if not user and 'username' in request.form:
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
    if request.form['confirm']:
        grant_user = user
    else:
        grant_user = None
    return authorization.create_authorization_response(grant_user=grant_user)


@bp.route('/oauth/token', methods=['POST'])
def issue_token():
    return authorization.create_token_response()


@bp.route('/oauth/revoke', methods=['POST'])
def revoke_token():
    return authorization.create_endpoint_response('revocation')


@bp.route('/api/me')
@require_oauth('profile')
def api_me():
    user_dn = current_token.authzSubject[0]
    user = User.get(user_dn)
    return jsonify(id=user.cn, name=user.sn)
