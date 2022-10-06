from flask import Blueprint

from . import authorizations
from . import clients
from . import consents
from . import endpoints
from . import tokens
from . import well_known

bp = Blueprint("oidc", __name__)

bp.register_blueprint(authorizations.bp)
bp.register_blueprint(clients.bp)
bp.register_blueprint(consents.bp)
bp.register_blueprint(endpoints.bp)
bp.register_blueprint(well_known.bp)
bp.register_blueprint(tokens.bp)
