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
]

slapd = slapd.Slapd(
    suffix="dc=mydomain,dc=tld",
    root_cn="admin",
    root_pw="admin",
    port=5389,
    log_level=logging.INFO,
    schemas=schemas,
)
slapd.start()

try:
    suffix_dc = slapd.suffix.split(",")[0][3:]
    slapd.ldapadd(
        "\n".join(
            [
                "dn: " + slapd.suffix,
                "objectClass: dcObject",
                "objectClass: organization",
                "dc: " + suffix_dc,
                "o: " + suffix_dc,
                "",
                "dn: " + slapd.root_dn,
                "objectClass: applicationProcess",
                "cn: " + slapd.root_cn,
            ]
        )
        + "\n"
    )

    for ldif in (
        "ldif/ppolicy.ldif",
        "ldif/bootstrap-users-tree.ldif",
        "ldif/bootstrap-oidc-tree.ldif",
    ):
        with open(ldif) as fd:
            try:
                slapd.ldapadd(fd.read())
            except RuntimeError:
                pass

    slapd.wait()
finally:
    slapd.stop()
