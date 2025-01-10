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
from ldap.controls.readentry import PostReadControl

from canaille.app import models
from canaille.app.configuration import ConfigurationException
from canaille.app.i18n import gettext as _
from canaille.backends import Backend
from canaille.backends import get_lockout_delay_message

from .utils import listify
from .utils import python_attrs_to_ldap


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


class LDAPBackend(Backend):
    def __init__(self, config):
        super().__init__(config)
        self._connection = None
        setup_ldap_models(config)

    @classmethod
    def install(cls, app):
        cls.setup_schemas(app.config)
        with cls(app.config).session():
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
                    emails=f"canaille_{uuid.uuid4()}@mydomain.example",
                    password="correct horse battery staple",
                )
                Backend.instance.save(user)
                Backend.instance.delete(user)

            except ldap.INSUFFICIENT_ACCESS as exc:
                raise ConfigurationException(
                    f"LDAP user '{config['CANAILLE_LDAP']['BIND_DN']}' cannot create "
                    f"users at '{config['CANAILLE_LDAP']['USER_BASE']}'"
                ) from exc

            try:
                models.Group.ldap_object_classes()

                user = models.User(
                    cn=f"canaille_{uuid.uuid4()}",
                    family_name=f"canaille_{uuid.uuid4()}",
                    user_name=f"canaille_{uuid.uuid4()}",
                    emails=f"canaille_{uuid.uuid4()}@mydomain.example",
                    password="correct horse battery staple",
                )
                Backend.instance.save(user)

                group = models.Group(
                    display_name=f"canaille_{uuid.uuid4()}",
                    members=[user],
                )
                Backend.instance.save(group)
                Backend.instance.delete(group)

            except ldap.INSUFFICIENT_ACCESS as exc:
                raise ConfigurationException(
                    f"LDAP user '{config['CANAILLE_LDAP']['BIND_DN']}' cannot create "
                    f"groups at '{config['CANAILLE_LDAP']['GROUP_BASE']}'"
                ) from exc

            finally:
                Backend.instance.delete(user)

    @classmethod
    def login_placeholder(cls):
        user_filter = current_app.config["CANAILLE_LDAP"]["USER_FILTER"]
        placeholders = []

        if "cn={{login" in user_filter.replace(" ", ""):
            placeholders.append(_("John Doe"))

        if "uid={{login" in user_filter.replace(" ", ""):
            placeholders.append(_("jdoe"))

        if "mail={{login" in user_filter.replace(" ", "") or not placeholders:
            placeholders.append(_("john.doe@example.com"))

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
        return self.get(User, filter=filter)

    def check_user_password(self, user, password):
        if current_app.features.has_intruder_lockout:
            if current_lockout_delay := user.get_intruder_lockout_delay():
                self.save(user)
                return (False, get_lockout_delay_message(current_lockout_delay))

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
        conn = self.connection
        conn.passwd_s(
            user.dn,
            None,
            password.encode("utf-8"),
        )

    def query(self, model, dn=None, filter=None, **kwargs):
        from .ldapobjectquery import LDAPObjectQuery

        base = dn
        if dn is None:
            base = f"{model.base},{model.root_dn}"
        elif "=" not in base:
            base = ldap.dn.escape_dn_chars(base)
            base = f"{model.rdn_attribute}={base},{model.base},{model.root_dn}"

        class_filter = (
            "".join([f"(objectClass={oc})" for oc in model.ldap_object_class])
            if model.ldap_object_class
            else ""
        )
        if class_filter:
            class_filter = f"(|{class_filter})"

        arg_filter = ""
        ldap_args = python_attrs_to_ldap(
            {
                model.python_attribute_to_ldap(name): values
                for name, values in kwargs.items()
                if values is not None
            },
            encode=False,
        )
        for key, value in ldap_args.items():
            if len(value) == 1:
                escaped_value = ldap.filter.escape_filter_chars(value[0])
                arg_filter += f"({key}={escaped_value})"

            else:
                values = [ldap.filter.escape_filter_chars(v) for v in value]
                arg_filter += (
                    "(|" + "".join([f"({key}={value})" for value in values]) + ")"
                )

        if not filter:
            filter = ""

        ldapfilter = f"(&{class_filter}{arg_filter}{filter})"
        base = base or f"{model.base},{model.root_dn}"
        try:
            result = self.connection.search_s(
                base, ldap.SCOPE_SUBTREE, ldapfilter or None, ["+", "*"]
            )
        except ldap.NO_SUCH_OBJECT:
            result = []
        return LDAPObjectQuery(model, result)

    def fuzzy(self, model, query, attributes=None, **kwargs):
        query = ldap.filter.escape_filter_chars(query)
        attributes = attributes or model.may() + model.must()
        attributes = [model.python_attribute_to_ldap(name) for name in attributes]
        filter = (
            "(|" + "".join(f"({attribute}=*{query}*)" for attribute in attributes) + ")"
        )
        return self.query(model, filter=filter, **kwargs)

    def get(self, model, identifier=None, /, **kwargs):
        try:
            return self.query(model, identifier, **kwargs)[0]
        except (IndexError, ldap.NO_SUCH_OBJECT):
            if identifier and model.base:
                return (
                    self.get(model, **{model.identifier_attribute: identifier})
                    or self.get(model, id=identifier)
                    or None
                )

            return None

    def save(self, instance):
        # run the instance save callback if existing
        save_callback = instance.save() if hasattr(instance, "save") else iter([])
        next(save_callback, None)

        current_object_classes = instance.get_ldap_attribute("objectClass") or []
        instance.set_ldap_attribute(
            "objectClass",
            list(set(instance.ldap_object_class) | set(current_object_classes)),
        )

        # PostReadControl allows to read the updated object attributes on creation/edition
        attributes = ["objectClass"] + [
            instance.python_attribute_to_ldap(name) for name in instance.attributes
        ]
        read_post_control = PostReadControl(criticality=True, attrList=attributes)

        # Object already exists in the LDAP database
        if instance.exists:
            deletions = [
                name
                for name, value in instance.changes.items()
                if (
                    value is None
                    or value == []
                    or (isinstance(value, list) and len(value) == 1 and not value[0])
                )
                and name in instance.state
            ]
            changes = {
                name: value
                for name, value in instance.changes.items()
                if name not in deletions and instance.state.get(name) != value
            }
            formatted_changes = python_attrs_to_ldap(changes, null_allowed=False)
            modlist = [(ldap.MOD_DELETE, name, None) for name in deletions] + [
                (ldap.MOD_REPLACE, name, values)
                for name, values in formatted_changes.items()
            ]
            _, _, _, [result] = self.connection.modify_ext_s(
                instance.dn, modlist, serverctrls=[read_post_control]
            )

        # Object does not exist yet in the LDAP database
        else:
            changes = {
                name: value
                for name, value in {**instance.state, **instance.changes}.items()
                if value and value[0]
            }
            formatted_changes = python_attrs_to_ldap(changes, null_allowed=False)
            modlist = [(name, values) for name, values in formatted_changes.items()]
            _, _, _, [result] = self.connection.add_ext_s(
                instance.dn, modlist, serverctrls=[read_post_control]
            )

        instance.exists = True
        instance.state = {**result.entry, **instance.changes}
        instance.changes = {}

        # run the instance save callback again if existing
        next(save_callback, None)

    def delete(self, instance):
        # run the instance delete callback if existing
        save_callback = instance.delete() if hasattr(instance, "delete") else iter([])
        next(save_callback, None)

        try:
            self.connection.delete_s(instance.dn)
        except ldap.NO_SUCH_OBJECT:
            pass

        # run the instance delete callback again if existing
        next(save_callback, None)

    def reload(self, instance):
        # run the instance reload callback if existing
        reload_callback = instance.reload() if hasattr(instance, "reload") else iter([])
        next(reload_callback, None)

        result = self.connection.search_s(
            instance.dn, ldap.SCOPE_SUBTREE, None, ["+", "*"]
        )
        instance.changes = {}
        instance.state = result[0][1]

        # run the instance reload callback again if existing
        next(reload_callback, None)


def setup_ldap_models(config):
    from canaille.app import models

    from .ldapobject import LDAPObject

    LDAPObject.root_dn = config["CANAILLE_LDAP"]["ROOT_DN"]

    user_base = config["CANAILLE_LDAP"]["USER_BASE"].replace(
        f",{config['CANAILLE_LDAP']['ROOT_DN']}", ""
    )
    models.User.base = user_base
    models.User.rdn_attribute = config["CANAILLE_LDAP"]["USER_RDN"]
    object_class = config["CANAILLE_LDAP"]["USER_CLASS"]
    models.User.ldap_object_class = listify(object_class)

    group_base = config["CANAILLE_LDAP"]["GROUP_BASE"].replace(
        f",{config['CANAILLE_LDAP']['ROOT_DN']}", ""
    )
    models.Group.base = group_base or None
    models.Group.rdn_attribute = config["CANAILLE_LDAP"]["GROUP_RDN"]
    object_class = config["CANAILLE_LDAP"]["GROUP_CLASS"]
    models.Group.ldap_object_class = listify(object_class)
