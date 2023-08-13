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
