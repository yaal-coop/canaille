import logging
import os
import pathlib

import slapd

CURRENT_DIR = pathlib.Path(__file__).parent
LDIF = CURRENT_DIR / "ldif"

schemas = [
    schema
    for schema in [
        "core.ldif",
        "cosine.ldif",
        "nis.ldif",
        "inetorgperson.ldif",
        "ppolicy.ldif",
    ]
    if os.path.exists(os.path.join(slapd.Slapd.SCHEMADIR, schema))
] + [
    str(LDIF / "memberof-config.ldif"),
    str(LDIF / "refint-config.ldif"),
    str(LDIF / "ppolicy-config.ldif"),
    str(LDIF / "otp-config.ldif"),
    str(LDIF / "oauth2-openldap.ldif"),
]

slapd = slapd.Slapd(
    suffix="dc=example,dc=org",
    root_cn="admin",
    root_pw="admin",
    host="0.0.0.0",
    port=5389,
    log_level=logging.INFO,
    schemas=schemas,
)
slapd.start()

try:
    slapd.init_tree()
    for ldif in (
        str(LDIF / "ppolicy.ldif"),
        str(LDIF / "bootstrap-users-tree.ldif"),
        str(LDIF / "bootstrap-oidc-tree.ldif"),
    ):
        try:
            slapd.ldapadd(None, ["-f", ldif])
        except RuntimeError:
            pass

    slapd.logger.info("slapd initialized: all ldif files loaded")
    slapd.wait()
finally:
    slapd.stop()
