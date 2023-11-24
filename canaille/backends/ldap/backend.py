import logging
import os
import uuid
from contextlib import contextmanager

import ldap.modlist
import ldif
from canaille.app import models
from canaille.app.configuration import ConfigurationException
from canaille.app.i18n import gettext as _
from canaille.app.themes import render_template
from canaille.backends import BaseBackend
from flask import current_app
from flask import request

from .utils import listify


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


class Backend(BaseBackend):
    def __init__(self, config):
        super().__init__(config)
        self.connection = None
        setup_ldap_models(config)

    @classmethod
    def install(cls, config, debug=False):
        cls.setup_schemas(config)
        with ldap_connection(config) as conn:
            models.Token.install(conn)
            models.AuthorizationCode.install(conn)
            models.Client.install(conn)
            models.Consent.install(conn)

    @classmethod
    def setup_schemas(cls, config):
        from .ldapobject import LDAPObject

        with ldap_connection(config) as conn:
            if "oauthClient" not in LDAPObject.ldap_object_classes(
                conn=conn, force=True
            ):
                install_schema(
                    config,
                    os.path.dirname(__file__) + "/schemas/oauth2-openldap.ldif",
                )

    def setup(self):
        if self.connection:
            return

        try:  # pragma: no cover
            if request.endpoint == "static":
                return
        except RuntimeError:  # pragma: no cover
            pass

        try:
            self.connection = ldap.initialize(self.config["BACKENDS"]["LDAP"]["URI"])
            self.connection.set_option(
                ldap.OPT_NETWORK_TIMEOUT,
                self.config["BACKENDS"]["LDAP"].get("TIMEOUT"),
            )
            self.connection.simple_bind_s(
                self.config["BACKENDS"]["LDAP"]["BIND_DN"],
                self.config["BACKENDS"]["LDAP"]["BIND_PW"],
            )

        except ldap.SERVER_DOWN:
            message = _("Could not connect to the LDAP server '{uri}'").format(
                uri=self.config["BACKENDS"]["LDAP"]["URI"]
            )
            logging.error(message)
            return (
                render_template(
                    "error.html",
                    error_code=500,
                    icon="database",
                    description=message,
                ),
                500,
            )

        except ldap.INVALID_CREDENTIALS:
            message = _("LDAP authentication failed with user '{user}'").format(
                user=self.config["BACKENDS"]["LDAP"]["BIND_DN"]
            )
            logging.error(message)
            return (
                render_template(
                    "error.html",
                    error_code=500,
                    icon="key",
                    description=message,
                ),
                500,
            )

    def teardown(self):
        try:  # pragma: no cover
            if request.endpoint == "static":
                return
        except RuntimeError:  # pragma: no cover
            pass

        if self.connection:  # pragma: no branch
            self.connection.unbind_s()
            self.connection = None

    @classmethod
    def validate(cls, config):
        from canaille.app import models

        try:
            conn = ldap.initialize(config["BACKENDS"]["LDAP"]["URI"])
            conn.set_option(
                ldap.OPT_NETWORK_TIMEOUT, config["BACKENDS"]["LDAP"].get("TIMEOUT")
            )
            conn.simple_bind_s(
                config["BACKENDS"]["LDAP"]["BIND_DN"],
                config["BACKENDS"]["LDAP"]["BIND_PW"],
            )

        except ldap.SERVER_DOWN as exc:
            raise ConfigurationException(
                f'Could not connect to the LDAP server \'{config["BACKENDS"]["LDAP"]["URI"]}\''
            ) from exc

        except ldap.INVALID_CREDENTIALS as exc:
            raise ConfigurationException(
                f'LDAP authentication failed with user \'{config["BACKENDS"]["LDAP"]["BIND_DN"]}\''
            ) from exc

        try:
            models.User.ldap_object_classes(conn)
            user = models.User(
                formatted_name=f"canaille_{uuid.uuid4()}",
                family_name=f"canaille_{uuid.uuid4()}",
                user_name=f"canaille_{uuid.uuid4()}",
                emails=f"canaille_{uuid.uuid4()}@mydomain.tld",
                password="correct horse battery staple",
            )
            user.save(conn)
            user.delete(conn)

        except ldap.INSUFFICIENT_ACCESS as exc:
            raise ConfigurationException(
                f'LDAP user \'{config["BACKENDS"]["LDAP"]["BIND_DN"]}\' cannot create '
                f'users at \'{config["BACKENDS"]["LDAP"]["USER_BASE"]}\''
            ) from exc

        try:
            models.Group.ldap_object_classes(conn)

            user = models.User(
                cn=f"canaille_{uuid.uuid4()}",
                family_name=f"canaille_{uuid.uuid4()}",
                user_name=f"canaille_{uuid.uuid4()}",
                emails=f"canaille_{uuid.uuid4()}@mydomain.tld",
                password="correct horse battery staple",
            )
            user.save(conn)

            group = models.Group(
                display_name=f"canaille_{uuid.uuid4()}",
                members=[user],
            )
            group.save(conn)
            group.delete(conn)

        except ldap.INSUFFICIENT_ACCESS as exc:
            raise ConfigurationException(
                f'LDAP user \'{config["BACKENDS"]["LDAP"]["BIND_DN"]}\' cannot create '
                f'groups at \'{config["BACKENDS"]["LDAP"]["GROUP_BASE"]}\''
            ) from exc

        finally:
            user.delete(conn)

        conn.unbind_s()

    @classmethod
    def login_placeholder(cls):
        user_filter = current_app.config["BACKENDS"]["LDAP"].get(
            "USER_FILTER", models.User.DEFAULT_FILTER
        )
        placeholders = []

        if "cn={{login" in user_filter.replace(" ", ""):
            placeholders.append(_("John Doe"))

        if "uid={{login" in user_filter.replace(" ", ""):
            placeholders.append(_("jdoe"))

        if "mail={{login" in user_filter.replace(" ", "") or not placeholders:
            placeholders.append(_("john@doe.com"))

        return _(" or ").join(placeholders)

    def has_account_lockability(self):
        from .ldapobject import LDAPObject

        try:
            return "pwdEndTime" in LDAPObject.ldap_object_attributes()
        except ldap.SERVER_DOWN:  # pragma: no cover
            return False


def setup_ldap_models(config):
    from .ldapobject import LDAPObject
    from canaille.app import models

    LDAPObject.root_dn = config["BACKENDS"]["LDAP"]["ROOT_DN"]

    user_base = config["BACKENDS"]["LDAP"]["USER_BASE"].replace(
        f',{config["BACKENDS"]["LDAP"]["ROOT_DN"]}', ""
    )
    models.User.base = user_base
    models.User.rdn_attribute = config["BACKENDS"]["LDAP"].get(
        "USER_RDN", models.User.DEFAULT_RDN
    )
    object_class = config["BACKENDS"]["LDAP"].get(
        "USER_CLASS", models.User.DEFAULT_OBJECT_CLASS
    )
    models.User.ldap_object_class = listify(object_class)

    group_base = (
        config["BACKENDS"]["LDAP"]
        .get("GROUP_BASE", "")
        .replace(f',{config["BACKENDS"]["LDAP"]["ROOT_DN"]}', "")
    )
    models.Group.base = group_base or None
    models.Group.rdn_attribute = config["BACKENDS"]["LDAP"].get(
        "GROUP_RDN", models.Group.DEFAULT_RDN
    )
    object_class = config["BACKENDS"]["LDAP"].get(
        "GROUP_CLASS", models.Group.DEFAULT_OBJECT_CLASS
    )
    models.Group.ldap_object_class = listify(object_class)
