from flask import Blueprint

from . import mail

bp = Blueprint("admin", __name__, url_prefix="/admin")

bp.register_blueprint(mail.bp)
