import logging
import os

import slapd

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
    "ldif/memberof-config.ldif",
    "ldif/refint-config.ldif",
    "ldif/ppolicy-config.ldif",
    "ldif/otp-config.ldif",
    "../canaille/backends/ldap/schemas/oauth2-openldap.ldif",
]

slapd = slapd.Slapd(
    suffix="dc=example,dc=org",
    root_cn="admin",
    root_pw="admin",
    port=5389,
    log_level=logging.INFO,
    schemas=schemas,
)
slapd.start()

try:
    slapd.init_tree()
    for ldif in (
        "ldif/ppolicy.ldif",
        "ldif/bootstrap-users-tree.ldif",
        "ldif/bootstrap-oidc-tree.ldif",
    ):
        try:
            slapd.ldapadd(None, ["-f", ldif])
        except RuntimeError:
            pass

    slapd.logger.info("slapd initialized: all ldif files loaded")
    slapd.wait()
finally:
    slapd.stop()
