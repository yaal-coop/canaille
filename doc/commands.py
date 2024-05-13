"""Temporary workaround for https://github.com/click-contrib/sphinx-click/issues/139"""

import inspect

import click

from canaille.backends.commands import create_factory
from canaille.backends.commands import delete_factory
from canaille.backends.commands import get_factory
from canaille.backends.commands import set_factory
from canaille.core.models import Group
from canaille.core.models import User
from canaille.oidc.basemodels import AuthorizationCode
from canaille.oidc.basemodels import Client
from canaille.oidc.basemodels import Consent
from canaille.oidc.basemodels import Token

MODELS = {
    "user": User,
    "group": Group,
    "client": Client,
    "authorizationcode": AuthorizationCode,
    "token": Token,
    "consent": Consent,
}


class ModelCommand(click.Group):
    def __init__(self, *args, factory, **kwargs):
        super().__init__(*args, **kwargs)
        self.factory = factory

    def list_commands(self, ctx):
        base = super().list_commands(ctx)
        lazy = sorted(MODELS.keys())
        return base + lazy

    def get_command(self, ctx, cmd_name):
        model = MODELS.get(cmd_name)
        return self.factory(model)


@click.command(cls=ModelCommand, factory=get_factory, help=inspect.getdoc(get_factory))
def get(): ...


@click.command(cls=ModelCommand, factory=set_factory, help=inspect.getdoc(set_factory))
def set(): ...


@click.command(
    cls=ModelCommand, factory=create_factory, help=inspect.getdoc(create_factory)
)
def create(): ...


@click.command(
    cls=ModelCommand, factory=delete_factory, help=inspect.getdoc(delete_factory)
)
def delete(): ...
