from contextlib import contextmanager

import ldap.modlist
import ldif


@contextmanager
def ldap_connection(config):
    conn = ldap.initialize(config["BACKENDS"]["LDAP"]["URI"])
    conn.set_option(ldap.OPT_NETWORK_TIMEOUT, config["BACKENDS"]["LDAP"].get("TIMEOUT"))
    conn.simple_bind_s(
        config["BACKENDS"]["LDAP"]["BIND_DN"], config["BACKENDS"]["LDAP"]["BIND_PW"]
    )

    try:
        yield conn
    finally:
        conn.unbind_s()


def install_schema(config, schema_path):
    from canaille.app.installation import InstallationException

    with open(schema_path) as fd:
        parser = ldif.LDIFRecordList(fd)
        parser.parse()

    try:
        with ldap_connection(config) as conn:
            for dn, entry in parser.all_records:
                add_modlist = ldap.modlist.addModlist(entry)
                conn.add_s(dn, add_modlist)

    except ldap.INSUFFICIENT_ACCESS as exc:
        raise InstallationException(
            f"The user '{config['BACKENDS']['LDAP']['BIND_DN']}' has insufficient permissions to install LDAP schemas."
        ) from exc
