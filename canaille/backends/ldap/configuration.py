from pydantic import Field

from canaille.app.configuration import BaseModel


class LDAPSettings(BaseModel):
    """Settings related to the LDAP backend.

    Belong in the ``CANAILLE_LDAP`` namespace.
    """

    URI: str = Field(
        "ldap://localhost", examples=["ldap://localhost", "ldaps://ldap.example.org"]
    )
    """The LDAP server URI."""

    ROOT_DN: str = "dc=example,dc=org"
    """The LDAP root DN."""

    BIND_DN: str = "cn=admin,dc=example,dc=org"
    """The LDAP bind DN."""

    BIND_PW: str = "admin"
    """The LDAP bind password."""

    TIMEOUT: float = 0.0
    """The LDAP connection timeout."""

    USER_BASE: str = Field(..., examples=["ou=users,dc=example,dc=org"])
    """The LDAP node under which users will be looked for and saved.

    For instance `ou=users,dc=example,dc=org`.
    """

    USER_CLASS: list[str] = ["inetOrgPerson"]
    """The object class to use for creating new users."""

    USER_RDN: str = "uid"
    """The attribute to identify an object in the User DN."""

    GROUP_BASE: str = Field(..., examples=["ou=groups,dc=example,dc=org"])
    """The LDAP node under which groups will be looked for and saved.

    For instance `"ou=groups,dc=example,dc=org"`.
    """

    GROUP_CLASS: str = "groupOfNames"
    """The object class to use for creating new groups."""

    GROUP_RDN: str = "cn"
    """The attribute to identify an object in the Group DN."""

    GROUP_NAME_ATTRIBUTE: str = "cn"
    """The attribute to use to identify a group."""
