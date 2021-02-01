import click
from flask import Blueprint, current_app
from canaille.models import AuthorizationCode, Token, Client


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


@bp.cli.command("clean")
@click.argument("command", type=click.Choice(["get", "create"]))
@click.option("--id")
@click.option("--name")
@click.option("--contact")
@click.option("--uri")
@click.option("--redirect-uri", multiple=True)
@click.option("--logo-uri")
@click.option("--secret")
@click.option("--secret-exp-date")
@click.option(
    "--grant-type",
    multiple=True,
    type=click.Choice(
        ["authorization_code", "refresh_token", "password", "hybrid", "implicit"]
    ),
)
@click.option(
    "--response-type", multiple=True, type=click.Choice(["code", "token", "id_token"])
)
@click.option("--scope", multiple=True)
@click.option("--tos-uri")
@click.option("--policy-uri")
@click.option("--jwk")
@click.option("--jwk-uri")
@click.option(
    "--token-endpoint-auth-method",
    multiple=True,
    type=click.Choice(["client_secret_basic", "none"]),
)
@click.option("--software-id")
@click.option("--software-version")
def client(
    command,
    id,
    name,
    contact,
    uri,
    redirect_uri,
    logo_uri,
    secret,
    secret_exp_date,
    grant_type,
    response_type,
    scope,
    tos_uri,
    policy_uri,
    jwk,
    jwk_uri,
    token_endpoint_auth_method,
    software_id,
    software_version,
):
    """
    Adds a client.
    """
    from canaille import setup_ldap, teardown_ldap

    setup_ldap(current_app)

    teardown_ldap(current_app)
