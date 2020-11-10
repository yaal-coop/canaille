import logging
import slapdtest
from slapdtest._slapdtest import combined_logger


class DevSlapdObject(slapdtest.SlapdObject):
    openldap_schema_files = (
        "core.ldif",
        "cosine.ldif",
        "nis.ldif",
        "inetorgperson.ldif",
        "../schemas/oauth2-openldap.ldif",
        "ldif/memberof.ldif"
    )
    suffix = "dc=mydomain,dc=tld"
    root_cn = "admin"
    root_pw = "admin"
    _log = combined_logger("slapd-demo-server", logging.INFO)

    def _avail_tcp_port(self):
        return 5389


slapd = DevSlapdObject()
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

    with open("ldif/bootstrap.ldif") as fd:
        slapd.ldapadd(fd.read())

    slapd.wait()
finally:
    slapd.stop()
