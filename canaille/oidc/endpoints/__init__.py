from flask import Blueprint

from . import authorizations
from . import clients
from . import consents
from . import oauth
from . import tokens
from . import well_known

bp = Blueprint("oidc", __name__, template_folder="../templates")

bp.register_blueprint(authorizations.bp)
bp.register_blueprint(clients.bp)
bp.register_blueprint(consents.bp)
bp.register_blueprint(oauth.bp)
bp.register_blueprint(well_known.bp)
bp.register_blueprint(tokens.bp)
