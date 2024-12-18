from flask import Blueprint

from . import account
from . import admin
from . import auth
from . import groups

bp = Blueprint("core", __name__)

bp.register_blueprint(account.bp)
bp.register_blueprint(admin.bp)
bp.register_blueprint(auth.bp)
bp.register_blueprint(groups.bp)
