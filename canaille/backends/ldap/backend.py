import logging
import os
import uuid
from contextlib import contextmanager

import ldap.modlist
import ldif
from flask import current_app
from ldap.controls import DecodeControlTuples
from ldap.controls.ppolicy import PasswordPolicyControl
from ldap.controls.ppolicy import PasswordPolicyError

from canaille.app import models
from canaille.app.configuration import ConfigurationException
from canaille.app.i18n import gettext as _
from canaille.backends import BaseBackend

from .utils import listify


@contextmanager
def ldap_connection(config):
    conn = ldap.initialize(config["CANAILLE_LDAP"]["URI"])
    conn.set_option(ldap.OPT_NETWORK_TIMEOUT, config["CANAILLE_LDAP"]["TIMEOUT"])
    conn.simple_bind_s(
        config["CANAILLE_LDAP"]["BIND_DN"], config["CANAILLE_LDAP"]["BIND_PW"]
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
            f"The user '{config['CANAILLE_LDAP']['BIND_DN']}' has insufficient permissions to install LDAP schemas."
        ) from exc


class Backend(BaseBackend):
    def __init__(self, config):
        super().__init__(config)
        self._connection = None
        setup_ldap_models(config)

    @classmethod
    def install(cls, config):
        cls.setup_schemas(config)
        with cls(config).session():
            models.Token.install()
            models.AuthorizationCode.install()
            models.Client.install()
            models.Consent.install()

    @classmethod
    def setup_schemas(cls, config):
        from .ldapobject import LDAPObject

        with cls(config).session():
            if "oauthClient" not in LDAPObject.ldap_object_classes(force=True):
                install_schema(
                    config,
                    os.path.dirname(__file__) + "/schemas/oauth2-openldap.ldif",
                )

    @property
    def connection(self):
        if self._connection:
            return self._connection

        try:
            self._connection = ldap.initialize(self.config["CANAILLE_LDAP"]["URI"])
            self._connection.set_option(
                ldap.OPT_NETWORK_TIMEOUT,
                self.config["CANAILLE_LDAP"]["TIMEOUT"],
            )
            self._connection.simple_bind_s(
                self.config["CANAILLE_LDAP"]["BIND_DN"],
                self.config["CANAILLE_LDAP"]["BIND_PW"],
            )

        except ldap.SERVER_DOWN as exc:
            message = _("Could not connect to the LDAP server '{uri}'").format(
                uri=self.config["CANAILLE_LDAP"]["URI"]
            )
            logging.error(message)
            raise ConfigurationException(message) from exc

        except ldap.INVALID_CREDENTIALS as exc:
            message = _("LDAP authentication failed with user '{user}'").format(
                user=self.config["CANAILLE_LDAP"]["BIND_DN"]
            )
            logging.error(message)
            raise ConfigurationException(message) from exc

        return self._connection

    def teardown(self):
        if self._connection:  # pragma: no branch
            self._connection.unbind_s()
            self._connection = None

    @classmethod
    def validate(cls, config):
        from canaille.app import models

        with cls(config).session():
            try:
                user = models.User(
                    formatted_name=f"canaille_{uuid.uuid4()}",
                    family_name=f"canaille_{uuid.uuid4()}",
                    user_name=f"canaille_{uuid.uuid4()}",
                    emails=f"canaille_{uuid.uuid4()}@mydomain.tld",
                    password="correct horse battery staple",
                )
                user.save()
                user.delete()

            except ldap.INSUFFICIENT_ACCESS as exc:
                raise ConfigurationException(
                    f'LDAP user \'{config["CANAILLE_LDAP"]["BIND_DN"]}\' cannot create '
                    f'users at \'{config["CANAILLE_LDAP"]["USER_BASE"]}\''
                ) from exc

            try:
                models.Group.ldap_object_classes()

                user = models.User(
                    cn=f"canaille_{uuid.uuid4()}",
                    family_name=f"canaille_{uuid.uuid4()}",
                    user_name=f"canaille_{uuid.uuid4()}",
                    emails=f"canaille_{uuid.uuid4()}@mydomain.tld",
                    password="correct horse battery staple",
                )
                user.save()

                group = models.Group(
                    display_name=f"canaille_{uuid.uuid4()}",
                    members=[user],
                )
                group.save()
                group.delete()

            except ldap.INSUFFICIENT_ACCESS as exc:
                raise ConfigurationException(
                    f'LDAP user \'{config["CANAILLE_LDAP"]["BIND_DN"]}\' cannot create '
                    f'groups at \'{config["CANAILLE_LDAP"]["GROUP_BASE"]}\''
                ) from exc

            finally:
                user.delete()

    @classmethod
    def login_placeholder(cls):
        user_filter = current_app.config["CANAILLE_LDAP"]["USER_FILTER"]
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

    def get_user_from_login(self, login=None):
        from .models import User

        raw_filter = current_app.config["CANAILLE_LDAP"]["USER_FILTER"]
        filter = (
            (
                current_app.jinja_env.from_string(raw_filter).render(
                    login=ldap.filter.escape_filter_chars(login)
                )
            )
            if login
            else None
        )
        return User.get(filter=filter)

    def check_user_password(self, user, password):
        conn = ldap.initialize(current_app.config["CANAILLE_LDAP"]["URI"])

        conn.set_option(
            ldap.OPT_NETWORK_TIMEOUT,
            current_app.config["CANAILLE_LDAP"]["TIMEOUT"],
        )

        message = None
        try:
            res = conn.simple_bind_s(
                user.dn, password, serverctrls=[PasswordPolicyControl()]
            )
            controls = res[3]
            result = True
        except ldap.INVALID_CREDENTIALS as exc:
            controls = DecodeControlTuples(exc.args[0]["ctrls"])
            result = False
        finally:
            conn.unbind_s()

        for control in controls:

            def gettext(x):
                return x

            if (
                control.controlType == PasswordPolicyControl.controlType
                and control.error == PasswordPolicyError.namedValues["accountLocked"]
            ):
                message = gettext("Your account has been locked.")
            elif (
                control.controlType == PasswordPolicyControl.controlType
                and control.error == PasswordPolicyError.namedValues["changeAfterReset"]
            ):
                message = gettext("You should change your password.")

        return result, message

    def set_user_password(self, user, password):
        conn = Backend.get().connection
        conn.passwd_s(
            user.dn,
            None,
            password.encode("utf-8"),
        )


def setup_ldap_models(config):
    from canaille.app import models

    from .ldapobject import LDAPObject

    LDAPObject.root_dn = config["CANAILLE_LDAP"]["ROOT_DN"]

    user_base = config["CANAILLE_LDAP"]["USER_BASE"].replace(
        f',{config["CANAILLE_LDAP"]["ROOT_DN"]}', ""
    )
    models.User.base = user_base
    models.User.rdn_attribute = config["CANAILLE_LDAP"]["USER_RDN"]
    object_class = config["CANAILLE_LDAP"]["USER_CLASS"]
    models.User.ldap_object_class = listify(object_class)

    group_base = config["CANAILLE_LDAP"]["GROUP_BASE"].replace(
        f',{config["CANAILLE_LDAP"]["ROOT_DN"]}', ""
    )
    models.Group.base = group_base or None
    models.Group.rdn_attribute = config["CANAILLE_LDAP"]["GROUP_RDN"]
    object_class = config["CANAILLE_LDAP"]["GROUP_CLASS"]
    models.Group.ldap_object_class = listify(object_class)
