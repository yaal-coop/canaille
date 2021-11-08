import ldap
from .models import Token, AuthorizationCode, Client, Consent


def install(config):
    setup_ldap_tree(config)


def setup_ldap_tree(config):
    conn = ldap.initialize(config["LDAP"]["URI"])
    if config["LDAP"].get("TIMEOUT"):
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, config["LDAP"]["TIMEOUT"])

    conn.simple_bind_s(config["LDAP"]["BIND_DN"], config["LDAP"]["BIND_PW"])
    Token.initialize(conn)
    AuthorizationCode.initialize(conn)
    Client.initialize(conn)
    Consent.initialize(conn)
    conn.unbind_s()
