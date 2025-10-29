import canaille.oidc.models

from .core import MemoryModel


class Client(canaille.oidc.models.Client, MemoryModel):
    pass


class AuthorizationCode(canaille.oidc.models.AuthorizationCode, MemoryModel):
    pass


class Token(canaille.oidc.models.Token, MemoryModel):
    pass


class Consent(canaille.oidc.models.Consent, MemoryModel):
    pass
