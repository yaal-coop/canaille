import click
import json
import sys
from flask import Blueprint, current_app
from canaille.models import Client


bp = Blueprint("commands.client", __name__, cli_group=None)


@bp.cli.command("client")
@click.argument(
    "command", type=click.Choice(["get", "edit", "create", "edit-or-create"])
)
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

    if command in ("get", "edit", "edit-or-create"):
        client = Client.get(id)

    if command == "edit-or-create":
        command = "edit" if client else "create"

    if command == "create":
        client = Client(
            id=id,
            name=name,
            contact=contact,
            uri=uri,
            redirect_uri=redirect_uri,
            logo_uri=logo_uri,
            secret=secret,
            secret_exp_date=secret_exp_date,
            grant_type=grant_type,
            response_type=response_type,
            scope=scope,
            tos_uri=tos_uri,
            policy_uri=policy_uri,
            jwk=jwk,
            jwk_uri=jwk_uri,
            token_endpoint_auth_method=token_endpoint_auth_method,
            software_id=software_id,
            software_version=software_version,
        ).save()

    if command == "edit":
        client.name = name
        client.contact = contact
        client.uri = uri
        client.redirect_uri = redirect_uri
        client.logo_uri = logo_uri
        client.secret = secret
        client.secret_exp_date = secret_exp_date
        client.grant_type = grant_type
        client.response_type = response_type
        client.scope = scope
        client.tos_uri = tos_uri
        client.policy_uri = policy_uri
        client.jwk = jwk
        client.jwk_uri = jwk_uri
        client.token_endpoint_auth_method = token_endpoint_auth_method
        client.software_id = software_id
        client.software_version = software_version
        client.save()

    json.dump(dict(client), sys.stdout, indent=4)

    teardown_ldap(current_app)
