import os

import slapd


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

        super().__init__(
            suffix="dc=mydomain,dc=tld",
            schemas=schemas,
        )

    def init_tree(self):
        suffix_dc = self.suffix.split(",")[0][3:]
        self.ldapadd(
            "\n".join(
                [
                    "dn: " + self.suffix,
                    "objectClass: dcObject",
                    "objectClass: organization",
                    "dc: " + suffix_dc,
                    "o: " + suffix_dc,
                    "",
                    "dn: " + self.root_dn,
                    "objectClass: applicationProcess",
                    "cn: " + self.root_cn,
                ]
            )
            + "\n"
        )
