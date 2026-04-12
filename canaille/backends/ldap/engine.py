from contextlib import contextmanager
from enum import Enum

import ldap
import ldap.modlist
import ldif
from ldap.controls import DecodeControlTuples
from ldap.controls.ppolicy import PasswordPolicyControl
from ldap.controls.ppolicy import PasswordPolicyError
from ldap.controls.readentry import PostReadControl
from ldappool import ConnectionManager
from ldappool import StateConnector

from .filter import build_attribute_filter
from .filter import build_class_filter
from .filter import build_fuzzy_filter
from .filter import build_search_filter
from .filter import resolve_base_dn
from .ldapobjectquery import LDAPObjectQuery
from .utils import is_meaningful_value
from .utils import python_attrs_to_ldap


class LDAPAlchemyError(Exception):
    """Base exception for all ldapalchemy errors."""


class OperationalError(LDAPAlchemyError):
    """The LDAP server is unreachable."""


class AuthenticationError(LDAPAlchemyError):
    """Invalid bind credentials."""


class InsufficientAccessError(LDAPAlchemyError):
    """Insufficient permissions for the requested operation."""


class NoSuchObjectError(LDAPAlchemyError):
    """The requested LDAP object does not exist."""


@contextmanager
def _wrap_ldap_errors():
    try:
        yield
    except ldap.SERVER_DOWN as exc:
        raise OperationalError(str(exc)) from exc
    except ldap.INVALID_CREDENTIALS as exc:
        raise AuthenticationError(str(exc)) from exc
    except ldap.INSUFFICIENT_ACCESS as exc:
        raise InsufficientAccessError(str(exc)) from exc
    except ldap.NO_SUCH_OBJECT as exc:
        raise NoSuchObjectError(str(exc)) from exc


def _make_connector_cls(network_timeout):
    """Create a StateConnector subclass that sets OPT_NETWORK_TIMEOUT."""

    class _Connector(StateConnector):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.set_option(ldap.OPT_NETWORK_TIMEOUT, network_timeout)

    return _Connector


class PasswordStatus(Enum):
    """Result of a password check operation."""

    SUCCESS = "success"
    INVALID_CREDENTIALS = "invalid_credentials"
    ACCOUNT_LOCKED = "account_locked"
    PASSWORD_MUST_CHANGE = "password_must_change"


class Engine:
    """LDAP connection pool and CRUD operations.

    Manages a pool of LDAP connections via ldappool and provides
    high-level operations for working with LDAP entries: query, save,
    delete, reload, and password management.

    All LDAP exceptions are wrapped into ldapalchemy exceptions so that
    consumers never need to import the ``ldap`` module directly.
    """

    def __init__(
        self,
        uri,
        bind_dn,
        bind_pw,
        root_dn,
        pool_size=10,
        pool_max_lifetime=600,
        pool_retry_max=3,
        pool_retry_delay=0.1,
        timeout=-1,
    ):
        self.uri = uri
        self.bind_dn = bind_dn
        self.bind_pw = bind_pw
        self.root_dn = root_dn
        self.timeout = timeout
        self.pool = ConnectionManager(
            uri=uri,
            bind=bind_dn,
            passwd=bind_pw,
            size=pool_size,
            max_lifetime=pool_max_lifetime,
            retry_max=pool_retry_max,
            retry_delay=pool_retry_delay,
            timeout=timeout,
            connector_cls=_make_connector_cls(timeout),
        )

    @contextmanager
    def connection(self):
        """Get a connection from the pool."""
        with _wrap_ldap_errors():
            with self.pool.connection() as conn:
                yield conn

    @contextmanager
    def _direct_connection(self, bind_dn=None, bind_pw=None):
        """Create a direct connection outside the pool."""
        conn = ldap.initialize(self.uri)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, self.timeout)
        conn.simple_bind_s(bind_dn or self.bind_dn, bind_pw or self.bind_pw)
        try:
            yield conn
        finally:
            conn.unbind_s()

    def check_password(self, user_dn, password):
        """Check a user password via LDAP bind.

        Performs a direct bind (outside the pool) with the given
        credentials and interprets password policy controls.
        """
        conn = ldap.initialize(self.uri)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, self.timeout)
        try:
            res = conn.simple_bind_s(
                user_dn, password, serverctrls=[PasswordPolicyControl()]
            )
            controls = res[3]
            status = PasswordStatus.SUCCESS
        except ldap.INVALID_CREDENTIALS as exc:
            controls = DecodeControlTuples(exc.args[0]["ctrls"])
            status = PasswordStatus.INVALID_CREDENTIALS
        finally:
            conn.unbind_s()

        for control in controls:
            if control.controlType != PasswordPolicyControl.controlType:
                continue
            if control.error == PasswordPolicyError.namedValues["accountLocked"]:
                status = PasswordStatus.ACCOUNT_LOCKED
            elif control.error == PasswordPolicyError.namedValues["changeAfterReset"]:
                status = PasswordStatus.PASSWORD_MUST_CHANGE

        return status

    def set_password(self, user_dn, password):
        """Set a user password via LDAP passwd extended operation."""
        with self.connection() as conn:
            conn.passwd_s(user_dn, None, password.encode("utf-8"))

    def install_schema(self, schema_path):
        """Install an LDAP schema from an LDIF file."""
        with open(schema_path) as fd:
            parser = ldif.LDIFRecordList(fd)
            parser.parse()

        with _wrap_ldap_errors():
            with self._direct_connection() as conn:
                for dn, entry in parser.all_records:
                    add_modlist = ldap.modlist.addModlist(entry)
                    conn.add_s(dn, add_modlist)

    def save(self, instance):
        """Persist an LDAPObject instance to the directory.

        Creates the entry if it does not exist, or updates it
        if it already exists. Uses PostReadControl to read back
        the entry state after the operation.
        """
        from .ldapobject import LDAPObject

        current_object_classes = instance.get_ldap_attribute("objectClass") or []
        instance.set_ldap_attribute(
            "objectClass",
            list(set(instance.ldap_object_class) | set(current_object_classes)),
        )

        available_attrs = LDAPObject.ldap_object_attributes()
        attributes = ["objectClass"] + [
            instance.python_attribute_to_ldap(name)
            for name in instance.attributes
            if instance.attribute_map
            and name in instance.attribute_map
            and instance.python_attribute_to_ldap(name) in available_attrs
        ]
        read_post_control = PostReadControl(criticality=True, attrList=attributes)

        if instance.exists:
            deletions = [
                name
                for name, value in instance._dirty.items()
                if (
                    not is_meaningful_value(value)
                    or (
                        isinstance(value, list)
                        and len(value) == 1
                        and not is_meaningful_value(value[0])
                    )
                )
                and name in instance._stored
            ]
            changes = {
                name: value
                for name, value in instance._dirty.items()
                if name not in deletions and instance._stored.get(name) != value
            }
            formatted_changes = python_attrs_to_ldap(changes, null_allowed=False)
            modlist = [(ldap.MOD_DELETE, name, None) for name in deletions] + [
                (ldap.MOD_REPLACE, name, values)
                for name, values in formatted_changes.items()
            ]
            with self.connection() as conn:
                _, _, _, [result] = conn.modify_ext_s(
                    instance.dn, modlist, serverctrls=[read_post_control]
                )
        else:
            changes = {
                name: value
                for name, value in {**instance._stored, **instance._dirty}.items()
                if value and is_meaningful_value(value[0])
            }
            formatted_changes = python_attrs_to_ldap(changes, null_allowed=False)
            modlist = [(name, values) for name, values in formatted_changes.items()]
            with self.connection() as conn:
                _, _, _, [result] = conn.add_ext_s(
                    instance.dn, modlist, serverctrls=[read_post_control]
                )

        instance.exists = True
        instance._stored = {**result.entry, **instance._dirty}
        instance._dirty = {}

    def delete(self, instance):
        """Delete an LDAPObject instance from the directory.

        Idempotent: does nothing if the entry does not exist.
        """
        try:
            with self.connection() as conn:
                conn.delete_s(instance.dn)
        except NoSuchObjectError:
            pass

    def reload(self, instance):
        """Reload an LDAPObject instance state from the directory."""
        with self.connection() as conn:
            result = conn.search_s(instance.dn, ldap.SCOPE_SUBTREE, None, ["+", "*"])
        instance._dirty = {}
        instance._stored = result[0][1]

    def query(self, model, dn=None, filter=None, **kwargs):
        """Query the directory for entries matching the given model and filters.

        Returns an empty collection if the base DN does not exist.
        """
        base = resolve_base_dn(model, dn)
        ldapfilter = build_search_filter(
            build_class_filter(model.ldap_object_class),
            build_attribute_filter(model, **kwargs),
            filter or "",
        )
        try:
            with self.connection() as conn:
                result = conn.search_s(base, ldap.SCOPE_SUBTREE, ldapfilter, ["+", "*"])
        except NoSuchObjectError:
            result = []
        return LDAPObjectQuery(model, result)

    def count(self, model, dn=None, filter=None, **kwargs):
        """Count entries matching the given model and filters without loading attributes."""
        base = resolve_base_dn(model, dn)
        ldapfilter = build_search_filter(
            build_class_filter(model.ldap_object_class),
            build_attribute_filter(model, **kwargs),
            filter or "",
        )
        try:
            with self.connection() as conn:
                result = conn.search_s(base, ldap.SCOPE_SUBTREE, ldapfilter, ["1.1"])
        except NoSuchObjectError:
            result = []
        return len(result)

    def get(self, model, identifier=None, /, **kwargs):
        """Return a single entry matching the criteria, or ``None``."""
        try:
            return self.query(model, identifier, **kwargs)[0]
        except (IndexError, NoSuchObjectError):
            if identifier and model.base:
                return (
                    self.get(model, **{model.identifier_attribute: identifier})
                    or self.get(model, id=identifier)
                    or None
                )
            return None

    def match_filter(self, dn, filter_str):
        """Check if an LDAP entry matches a filter string."""
        with self.connection() as conn:
            return bool(conn.search_s(dn, ldap.SCOPE_SUBTREE, filter_str))

    def fuzzy(self, model, query, attributes=None, **kwargs):
        """Query the directory with substring matching on the given attributes."""
        attributes = attributes or model.may() + model.must()
        ldap_attributes = [model.python_attribute_to_ldap(name) for name in attributes]
        filter = build_fuzzy_filter(query, ldap_attributes)
        return self.query(model, filter=filter, **kwargs)
