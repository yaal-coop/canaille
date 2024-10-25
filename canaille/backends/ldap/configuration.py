from pydantic import BaseModel


class LDAPSettings(BaseModel):
    """Settings related to the LDAP backend.

    Belong in the ``CANAILLE_LDAP`` namespace.
    """

    URI: str = "ldap://localhost"
    """The LDAP server URI."""

    ROOT_DN: str = "dc=mydomain,dc=tld"
    """The LDAP root DN."""

    BIND_DN: str = "cn=admin,dc=mydomain,dc=tld"
    """The LDAP bind DN."""

    BIND_PW: str = "admin"
    """The LDAP bind password."""

    TIMEOUT: float = 0.0
    """The LDAP connection timeout."""

    USER_BASE: str
    """The LDAP node under which users will be looked for and saved.

    For instance `ou=users,dc=mydomain,dc=tld`.
    """

    USER_CLASS: list[str] = ["inetOrgPerson"]
    """The object class to use for creating new users."""

    USER_RDN: str = "uid"
    """The attribute to identify an object in the User DN."""

    USER_FILTER: str = "(|(uid={{ login }})(mail={{ login }}))"
    """Filter to match users on sign in.

    For instance ``(|(uid={{ login }})(mail={{ login }}))``.
    Jinja syntax is supported and a ``login`` variable is available,
    containing the value passed in the login field.
    """

    GROUP_BASE: str
    """The LDAP node under which groups will be looked for and saved.

    For instance `"ou=groups,dc=mydomain,dc=tld"`.
    """

    GROUP_CLASS: str = "groupOfNames"
    """The object class to use for creating new groups."""

    GROUP_RDN: str = "cn"
    """The attribute to identify an object in the Group DN."""

    GROUP_NAME_ATTRIBUTE: str = "cn"
    """The attribute to use to identify a group."""
