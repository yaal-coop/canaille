from flask import Blueprint, current_app
from canaille.models import AuthorizationCode, Token


bp = Blueprint("commands", __name__, cli_group=None)


@bp.cli.command("clean")
def clean():
    """
    Remove expired tokens and authorization codes.
    """
    from canaille import setup_ldap, teardown_ldap

    setup_ldap(current_app)

    for t in Token.filter():
        if t.is_expired():
            t.delete()

    for a in AuthorizationCode.filter():
        if a.is_expired():
            a.delete()

    teardown_ldap(current_app)
