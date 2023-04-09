import logging
import uuid

import ldap
from canaille.backends import Backend
from flask import render_template
from flask import request
from flask_babel import gettext as _


class LDAPBackend(Backend):
    def __init__(self, config):
        from canaille.oidc.installation import setup_ldap_tree

        super().__init__(config)
        self.config = config
        self.connection = None
        setup_ldap_models(config)
        setup_ldap_tree(config)

    def setup(self):
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
                    error=500,
                    icon="database",
                    debug=self.config.get("DEBUG", False),
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
                    error=500,
                    icon="key",
                    debug=self.config.get("DEBUG", False),
                    description=message,
                ),
                500,
            )

    def teardown(self):
        if self.connection:  # pragma: no branch
            self.connection.unbind_s()
            self.connection = None

    @classmethod
    def validate(cls, config):
        from canaille.app.configuration import ConfigurationException
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
                email=f"canaille_{uuid.uuid4()}@mydomain.tld",
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
                email=f"canaille_{uuid.uuid4()}@mydomain.tld",
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


def setup_ldap_models(config):
    from .ldapobject import LDAPObject
    from canaille.app import models

    LDAPObject.root_dn = config["BACKENDS"]["LDAP"]["ROOT_DN"]

    user_base = config["BACKENDS"]["LDAP"]["USER_BASE"].replace(
        f',{config["BACKENDS"]["LDAP"]["ROOT_DN"]}', ""
    )
    models.User.base = user_base
    models.User.rdn_attribute = config["BACKENDS"]["LDAP"].get(
        "USER_ID_ATTRIBUTE", models.User.DEFAULT_ID_ATTRIBUTE
    )
    object_class = config["BACKENDS"]["LDAP"].get(
        "USER_CLASS", models.User.DEFAULT_OBJECT_CLASS
    )
    models.User.ldap_object_class = (
        object_class if isinstance(object_class, list) else [object_class]
    )

    group_base = (
        config["BACKENDS"]["LDAP"]
        .get("GROUP_BASE", "")
        .replace(f',{config["BACKENDS"]["LDAP"]["ROOT_DN"]}', "")
    )
    models.Group.base = group_base or None
    models.Group.rdn_attribute = config["BACKENDS"]["LDAP"].get(
        "GROUP_ID_ATTRIBUTE", models.Group.DEFAULT_ID_ATTRIBUTE
    )
    object_class = config["BACKENDS"]["LDAP"].get(
        "GROUP_CLASS", models.Group.DEFAULT_OBJECT_CLASS
    )
    models.Group.ldap_object_class = (
        object_class if isinstance(object_class, list) else [object_class]
    )
