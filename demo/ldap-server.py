import logging

import slapd


slapd = slapd.Slapd(
    suffix="dc=mydomain,dc=tld",
    root_cn="admin",
    root_pw="admin",
    port=5389,
    log_level=logging.INFO,
    schemas=(
        "core.ldif",
        "cosine.ldif",
        "nis.ldif",
        "inetorgperson.ldif",
        "../schemas/oauth2-openldap.ldif",
        "ldif/memberof.ldif",
    ),
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

    with open("ldif/bootstrap-tree.ldif") as fd:
        try:
            slapd.ldapadd(fd.read())
        except RuntimeError:
            pass

    with open("ldif/bootstrap-data.ldif") as fd:
        try:
            slapd.ldapadd(fd.read())
        except RuntimeError:
            pass

    slapd.wait()
finally:
    slapd.stop()
