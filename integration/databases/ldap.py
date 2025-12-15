import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from integration.runners.base import CanailleRunner


class LDAPConfig:
    """LDAP database configuration provider."""

    def get_config(
        self, workdir: Path, build_type: str, request: pytest.FixtureRequest
    ) -> str:
        slapd = request.getfixturevalue("slapd_server")
        return f"""\
DATABASE = "ldap"

[CANAILLE_LDAP]
ROOT_DN = "{slapd.suffix}"
URI = "{slapd.ldap_uri}"
BIND_DN = "{slapd.root_dn}"
BIND_PW = "{slapd.root_pw}"
USER_BASE = "ou=users"
USER_RDN = "uid"
GROUP_BASE = "ou=groups"
TIMEOUT = 5
USER_CLASS = ["inetOrgPerson"]
"""

    def setup(
        self,
        runner: "CanailleRunner",
        config_path: Path,
        workdir: Path,
    ) -> None:
        pass


def create_slapd_server():
    """Create and configure a LDAP server for testing."""
    slapd = pytest.importorskip("slapd")

    class CustomSlapdObject(slapd.Slapd):
        def __init__(self):
            schemas = [
                schema
                for schema in [
                    "core.ldif",
                    "cosine.ldif",
                    "nis.ldif",
                    "inetorgperson.ldif",
                    "ppolicy.ldif",
                ]
                if os.path.exists(os.path.join(self.SCHEMADIR, schema))
            ]
            super().__init__(suffix="dc=example,dc=org", schemas=schemas)

    server = CustomSlapdObject()
    server.start()
    server.init_tree()
    for ldif in (
        "dev/ldif/memberof-config.ldif",
        "dev/ldif/ppolicy-config.ldif",
        "dev/ldif/ppolicy.ldif",
        "dev/ldif/otp-config.ldif",
        "canaille/backends/ldap/schemas/oauth2-openldap.ldif",
        "dev/ldif/bootstrap-users-tree.ldif",
        "dev/ldif/bootstrap-oidc-tree.ldif",
    ):
        server.ldapadd(None, ["-f", ldif])
    return server
