import inspect
import logging
import os
import uuid
from contextlib import contextmanager

from flask import current_app

from canaille.app import models
from canaille.app.configuration import CheckResult
from canaille.app.configuration import ConfigurationException
from canaille.app.i18n import gettext as _
from canaille.app.models import MODELS
from canaille.backends import Backend
from canaille.backends import ModelEncoder
from canaille.backends import get_lockout_delay_message
from canaille.backends import is_meaningful_value
from canaille.backends.models import Model

from .engine import AuthenticationError
from .engine import Engine
from .engine import InsufficientAccessError
from .engine import OperationalError
from .engine import PasswordStatus
from .utils import listify


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

        return value.id if value is not None else None

    def default(self, obj):
        if isinstance(obj, Model):
            sanitized_state = {
                attr: self.sanitize_attr(obj, attr) for attr in obj.attributes
            }
            return {
                key: value
                for key, value in sanitized_state.items()
                if is_meaningful_value(value)
            }
        return super().default(obj)


class LDAPBackend(Backend):
    json_encoder = LDAPModelEncoder

    def __init__(self, config):
        super().__init__(config)
        ldap_config = self.config["CANAILLE_LDAP"]
        self.engine = Engine(
            uri=ldap_config["URI"],
            bind_dn=ldap_config["BIND_DN"],
            bind_pw=ldap_config["BIND_PW"],
            root_dn=ldap_config["ROOT_DN"],
            pool_size=ldap_config["POOL_SIZE"],
            pool_max_lifetime=ldap_config["POOL_MAX_LIFETIME"],
            pool_retry_max=ldap_config["POOL_RETRY_MAX"],
            pool_retry_delay=ldap_config["POOL_RETRY_DELAY"],
            timeout=ldap_config["TIMEOUT"],
        )

    def init_app(self, app, init_backend=None):
        super().init_app(app, init_backend)
        setup_ldap_models(self.config)

    @classmethod
    def install(cls, app):
        cls.setup_schemas(app.config)
        if app.features.has_oidc:
            with cls(app.config).session():
                models.Token.install()
                models.AuthorizationCode.install()
                models.Client.install()
                models.Consent.install()

    @classmethod
    def setup_schemas(cls, config):
        from canaille.app.installation import InstallationException

        from .ldapobject import LDAPObject

        with cls(config).session():
            if "oauthClient" not in LDAPObject.ldap_object_classes(force=True):
                try:
                    Backend.instance.engine.install_schema(
                        os.path.dirname(__file__) + "/schemas/oauth2-openldap.ldif",
                    )
                except InsufficientAccessError as exc:
                    raise InstallationException(
                        f"The user '{config['CANAILLE_LDAP']['BIND_DN']}' has insufficient permissions to install LDAP schemas."
                    ) from exc

    @contextmanager
    def connection(self):
        """Get a connection from the pool."""
        with self.engine.connection() as conn:
            yield conn

    @classmethod
    def check_network_config(cls, config):
        from canaille.app import models

        previous_instance = Backend._instance
        try:
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

                except InsufficientAccessError:
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

                except InsufficientAccessError:
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

        except OperationalError as exc:
            message = _("Could not connect to the LDAP server '{uri}'").format(
                uri=config["CANAILLE_LDAP"]["URI"]
            )
            logging.error(message)
            raise ConfigurationException(message) from exc

        except AuthenticationError as exc:
            message = _("LDAP authentication failed with user '{user}'").format(
                user=config["CANAILLE_LDAP"]["BIND_DN"]
            )
            logging.error(message)
            raise ConfigurationException(message) from exc

        finally:
            Backend._instance = previous_instance

    def has_account_lockability(self) -> bool:
        from .ldapobject import LDAPObject

        try:
            return "pwdEndTime" in LDAPObject.ldap_object_attributes()
        except OperationalError:  # pragma: no cover
            return False

    def has_otp_support(self) -> bool:
        from .ldapobject import LDAPObject

        try:
            return "oathSecret" in LDAPObject.ldap_object_attributes()
        except OperationalError:  # pragma: no cover
            return False

    def check_user_password(self, user, password):
        if current_app.features.has_intruder_lockout:
            if current_lockout_delay := user.get_intruder_lockout_delay():
                self.save(user)
                return (False, get_lockout_delay_message(current_lockout_delay))

        status = self.engine.check_password(user.dn, password)

        result = status in (PasswordStatus.SUCCESS, PasswordStatus.PASSWORD_MUST_CHANGE)
        messages = {
            PasswordStatus.ACCOUNT_LOCKED: "Your account has been locked.",
            PasswordStatus.PASSWORD_MUST_CHANGE: "You should change your password.",
        }
        return result, messages.get(status)

    def set_user_password(self, user, password) -> None:
        self.engine.set_password(user.dn, password)

    def do_query(self, model, *args, **kwargs):
        return self.engine.query(model, *args, **kwargs)

    def fuzzy(self, model, query, attributes=None, **kwargs):
        return self.engine.fuzzy(model, query, attributes, **kwargs)

    def get(self, model, identifier=None, /, **kwargs):
        return self.engine.get(model, identifier, **kwargs)

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

    def do_save(self, instance) -> None:
        self.engine.save(instance)

    def do_delete(self, instance) -> None:
        self.engine.delete(instance)

    def do_reload(self, instance) -> None:
        self.engine.reload(instance)


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
