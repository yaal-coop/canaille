import inspect
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
from canaille.app.configuration import CheckResult
from canaille.app.configuration import ConfigurationException
from canaille.app.i18n import gettext as _
from canaille.app.models import MODELS
from canaille.backends import Backend
from canaille.backends import ModelEncoder
from canaille.backends import get_lockout_delay_message
from canaille.backends.models import Model

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


class LDAPModelEncoder(ModelEncoder):
    def sanitize_attr(self, obj, attr):
        """Replace dns by uuids in model attributes."""
        value = getattr(obj, attr)
        type_, _ = obj.get_model_annotations(attr)
        is_model = inspect.isclass(type_) and issubclass(type_, Model)
        if not is_model:
            return value

        if isinstance(value, list):
            return [item.id for item in value]

        return value.id

    def default(self, obj):
        if isinstance(obj, Model):
            sanitized_state = {
                attr: self.sanitize_attr(obj, attr) for attr in obj.attributes
            }
            return {key: value for key, value in sanitized_state.items() if value}
        return super().default(obj)


class LDAPBackend(Backend):
    json_encoder = LDAPModelEncoder

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
    def check_network_config(cls, config):
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

            except ldap.INSUFFICIENT_ACCESS:
                return CheckResult(
                    message=f"LDAP user '{config['CANAILLE_LDAP']['BIND_DN']}' cannot create "
                    f"users at '{config['CANAILLE_LDAP']['USER_BASE']}'",
                    success=False,
                )

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

            except ldap.INSUFFICIENT_ACCESS:
                return CheckResult(
                    message=f"LDAP user '{config['CANAILLE_LDAP']['BIND_DN']}' cannot create "
                    f"groups at '{config['CANAILLE_LDAP']['GROUP_BASE']}'",
                    success=False,
                )

            finally:
                Backend.instance.delete(user)

        return CheckResult(
            message="The connection to the LDAP server and permissions of the bind DN are correct",
            success=True,
        )

    def has_account_lockability(self):
        from .ldapobject import LDAPObject

        try:
            return "pwdEndTime" in LDAPObject.ldap_object_attributes()
        except ldap.SERVER_DOWN:  # pragma: no cover
            return False

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

    def do_query(self, model, dn=None, filter=None, *args, **kwargs):
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

    def do_restore(self, payload):
        # Canaille exports uuids but LDAP uuids are read-only
        # thus uuids will probably be replaced by LDAP.
        # However as they server as identifiers in the dumps,
        # we need to keep a temporary uuid <-> dn mapping
        uuids_dn = {}

        # Create models without attributes that are references to other models
        # except when those attributes are required
        # We *could* do this in one single loop, but Client.audience is self-referencing,
        # so it has to be created first, and then must be added to its own audience.
        for model_name, model in MODELS.items():
            states = payload.get(model_name, [])
            for state in states:
                filtered_state = self.filter_state(
                    model, state, keep_non_model_and_required_attrs=True
                )
                filtered_state = self.replace_uuids_with_dns(
                    model, filtered_state, uuids_dn
                )
                obj = model(**filtered_state)
                Backend.instance.save(obj)
                uuids_dn[state["id"]] = obj.dn

        # Insert attributes that are model references
        for model_name, model in MODELS.items():
            states = payload.get(model_name, [])
            for state in states:
                obj_dn = uuids_dn[state["id"]]
                filtered_state = self.filter_state(
                    model,
                    state,
                    keep_non_model_and_required_attrs=False,
                )
                filtered_state = self.replace_uuids_with_dns(
                    model, filtered_state, uuids_dn
                )
                obj = Backend.instance.get(model, obj_dn)
                for attr, value in filtered_state.items():
                    setattr(obj, attr, value)
                Backend.instance.save(obj)

    @classmethod
    def filter_state(cls, model, state, keep_non_model_and_required_attrs):
        def filter_attribute(attr):
            type_, _ = model.get_model_annotations(attr)
            is_non_model = not inspect.isclass(type_) or not issubclass(type_, Model)
            is_required = model.is_attr_required(attr)
            is_writable = not model.is_attr_readonly(attr)
            valid = (
                is_writable
                and (is_non_model or is_required) == keep_non_model_and_required_attrs
            )
            return valid

        return {attr: value for attr, value in state.items() if filter_attribute(attr)}

    @classmethod
    def replace_uuids_with_dns(cls, model, state, uuids_dn):
        def get_dn_from_uuid(uuid, model):
            backend_model = MODELS.get(model.__name__.lower())
            return uuids_dn.get(uuid) or Backend.instance.get(backend_model, id=uuid).dn

        def replace_attr(attr, value):
            type_, _ = model.get_model_annotations(attr)
            is_model = inspect.isclass(type_) and issubclass(type_, Model)
            if not is_model:
                return value

            if isinstance(value, list):
                return [get_dn_from_uuid(item, type_) for item in value]

            return get_dn_from_uuid(value, type_)

        return {attr: replace_attr(attr, value) for attr, value in state.items()}

    def do_save(self, instance):
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

    def do_delete(self, instance):
        try:
            self.connection.delete_s(instance.dn)
        except ldap.NO_SUCH_OBJECT:
            pass

    def do_reload(self, instance):
        result = self.connection.search_s(
            instance.dn, ldap.SCOPE_SUBTREE, None, ["+", "*"]
        )
        instance.changes = {}
        instance.state = result[0][1]


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
