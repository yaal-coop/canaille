from flask import Blueprint

from . import authorizations
from . import clients
from . import mail
from . import tokens

bp = Blueprint("admin", __name__)

bp.register_blueprint(tokens.bp, url_prefix="/token")
bp.register_blueprint(authorizations.bp, url_prefix="/authorization")
bp.register_blueprint(clients.bp, url_prefix="/client")
bp.register_blueprint(mail.bp, url_prefix="/mail")
