import typing

import ldap.dn
import ldap.filter
from ldap.controls.readentry import PostReadControl

from canaille.backends import BaseBackend
from canaille.backends.models import BackendModel

from .backend import Backend
from .utils import attribute_ldap_syntax
from .utils import cardinalize_attribute
from .utils import ldap_to_python
from .utils import listify
from .utils import python_attrs_to_ldap


class LDAPObjectMetaclass(type):
    ldap_to_python_class = {}

    def __new__(cls, name, bases, attrs):
        klass = super().__new__(cls, name, bases, attrs)
        if attrs.get("ldap_object_class"):
            for oc in attrs["ldap_object_class"]:
                cls.ldap_to_python_class[oc] = klass
        return klass

    def __setattr__(cls, name, value):
        super().__setattr__(name, value)
        if name == "ldap_object_class":
            for oc in value:
                cls.ldap_to_python_class[oc] = cls


class LDAPObject(BackendModel, metaclass=LDAPObjectMetaclass):
    _object_class_by_name = None
    _attribute_type_by_name = None
    _may = None
    _must = None
    base = None
    root_dn = None
    rdn_attribute = None
    attribute_map = None
    ldap_object_class = None

    def __init__(self, dn=None, **kwargs):
        self.state = {}
        self.changes = {}
        self.exists = False

        for name, value in kwargs.items():
            setattr(self, name, value)

    def __repr__(self):
        attribute_name = self.ldap_attribute_to_python(self.rdn_attribute)
        return (
            f"<{self.__class__.__name__} {attribute_name}={self.rdn_value}>"
            if self.rdn_attribute
            else "<LDAPOBject>"
        )

    def __eq__(self, other):
        ldap_attributes = self.may() + self.must()

        if not (
            isinstance(other, self.__class__)
            and self.may() == other.may()
            and self.must() == other.must()
            and all(
                self.has_ldap_attribute(attr) == other.has_ldap_attribute(attr)
                for attr in ldap_attributes
            )
        ):
            return False

        self_attributes = python_attrs_to_ldap(
            {
                attr: self.get_ldap_attribute(attr)
                for attr in ldap_attributes
                if self.has_ldap_attribute(attr)
            }
        )
        other_attributes = python_attrs_to_ldap(
            {
                attr: other.get_ldap_attribute(attr)
                for attr in ldap_attributes
                if other.has_ldap_attribute(attr)
            }
        )
        return self_attributes == other_attributes

    def __hash__(self):
        return hash(self.id)

    def __getattribute__(self, name):
        if name == "attributes" or name not in self.attributes:
            return super().__getattribute__(name)

        ldap_name = self.python_attribute_to_ldap(name)

        python_single_value = typing.get_origin(self.attributes[name]) is not list
        ldap_value = self.get_ldap_attribute(ldap_name)
        return cardinalize_attribute(python_single_value, ldap_value)

    def __setattr__(self, name, value):
        if name not in self.attributes:
            super().__setattr__(name, value)

        ldap_name = self.python_attribute_to_ldap(name)
        self.set_ldap_attribute(ldap_name, value)

    def has_ldap_attribute(self, name):
        return name in self.ldap_object_attributes() and (
            name in self.changes or name in self.state
        )

    def get_ldap_attribute(self, name):
        if name in self.changes:
            return self.changes[name]

        if not self.state.get(name):
            return None

        # Lazy conversion from ldap format to python format
        if any(isinstance(value, bytes) for value in self.state[name]):
            syntax = attribute_ldap_syntax(name)
            self.state[name] = [
                ldap_to_python(value, syntax) for value in self.state[name]
            ]

        return self.state.get(name)

    def set_ldap_attribute(self, name, value):
        if name not in self.ldap_object_attributes():
            return

        value = listify(value)
        self.changes[name] = value

    @property
    def rdn_value(self):
        value = self.get_ldap_attribute(self.rdn_attribute)
        return (value[0] if isinstance(value, list) else value).strip()

    @property
    def dn(self):
        return self.dn_for(self.rdn_value)

    @classmethod
    def dn_for(cls, rdn):
        return f"{cls.rdn_attribute}={ldap.dn.escape_dn_chars(rdn)},{cls.base},{cls.root_dn}"

    @classmethod
    def may(cls):
        if not cls._may:
            cls.update_ldap_attributes()
        return cls._may

    @classmethod
    def must(cls):
        return cls._must

    @classmethod
    def install(cls):
        conn = Backend.instance.connection
        cls.ldap_object_classes(conn)
        cls.ldap_object_attributes(conn)

        acc = ""
        for organizationalUnit in cls.base.split(",")[::-1]:
            v = organizationalUnit.split("=")[1]
            dn = f"{organizationalUnit}{acc},{cls.root_dn}"
            acc = f",{organizationalUnit}"
            try:
                conn.add_s(
                    dn,
                    [
                        ("objectClass", [b"organizationalUnit"]),
                        ("ou", [v.encode("utf-8")]),
                    ],
                )
            except ldap.ALREADY_EXISTS:
                pass

    @classmethod
    def ldap_object_classes(cls, force=False):
        if cls._object_class_by_name and not force:
            return cls._object_class_by_name

        conn = Backend.instance.connection

        res = conn.search_s(
            "cn=subschema", ldap.SCOPE_BASE, "(objectclass=*)", ["*", "+"]
        )
        subschema_entry = res[0]
        subschema_subentry = ldap.cidict.cidict(subschema_entry[1])
        subschema = ldap.schema.SubSchema(subschema_subentry)
        object_class_oids = subschema.listall(ldap.schema.models.ObjectClass)
        cls._object_class_by_name = {}
        for oid in object_class_oids:
            object_class = subschema.get_obj(ldap.schema.models.ObjectClass, oid)
            for name in object_class.names:
                cls._object_class_by_name[name] = object_class

        return cls._object_class_by_name

    @classmethod
    def ldap_object_attributes(cls, force=False):
        if cls._attribute_type_by_name and not force:
            return cls._attribute_type_by_name

        conn = Backend.instance.connection

        res = conn.search_s(
            "cn=subschema", ldap.SCOPE_BASE, "(objectclass=*)", ["*", "+"]
        )
        subschema_entry = res[0]
        subschema_subentry = ldap.cidict.cidict(subschema_entry[1])
        subschema = ldap.schema.SubSchema(subschema_subentry)
        attribute_type_oids = subschema.listall(ldap.schema.models.AttributeType)
        cls._attribute_type_by_name = {}
        for oid in attribute_type_oids:
            object_class = subschema.get_obj(ldap.schema.models.AttributeType, oid)
            for name in object_class.names:
                cls._attribute_type_by_name[name] = object_class

        return cls._attribute_type_by_name

    @classmethod
    def get(cls, identifier=None, /, **kwargs):
        try:
            return BaseBackend.instance.query(cls, identifier, **kwargs)[0]
        except (IndexError, ldap.NO_SUCH_OBJECT):
            if identifier and cls.base:
                return (
                    cls.get(**{cls.identifier_attribute: identifier})
                    or cls.get(id=identifier)
                    or None
                )

            return None

    @classmethod
    def update_ldap_attributes(cls):
        all_object_classes = cls.ldap_object_classes()
        this_object_classes = {
            all_object_classes[name] for name in cls.ldap_object_class
        }
        done = set()

        cls._may = []
        cls._must = []
        while len(this_object_classes) > 0:
            object_class = this_object_classes.pop()
            done.add(object_class)
            this_object_classes |= {
                all_object_classes[ocsup]
                for ocsup in object_class.sup
                if ocsup not in done
            }
            cls._may.extend(object_class.may)
            cls._must.extend(object_class.must)

        cls._may = list(set(cls._may))
        cls._must = list(set(cls._must))

    @classmethod
    def ldap_attribute_to_python(cls, name):
        reverse_attribute_map = {v: k for k, v in (cls.attribute_map or {}).items()}
        return reverse_attribute_map.get(name, name)

    @classmethod
    def python_attribute_to_ldap(cls, name):
        return cls.attribute_map.get(name, name) if cls.attribute_map else None

    def reload(self):
        conn = Backend.instance.connection
        result = conn.search_s(self.dn, ldap.SCOPE_SUBTREE, None, ["+", "*"])
        self.changes = {}
        self.state = result[0][1]

    def save(self):
        conn = Backend.instance.connection

        current_object_classes = self.get_ldap_attribute("objectClass") or []
        self.set_ldap_attribute(
            "objectClass",
            list(set(self.ldap_object_class) | set(current_object_classes)),
        )

        # PostReadControl allows to read the updated object attributes on creation/edition
        attributes = ["objectClass"] + [
            self.python_attribute_to_ldap(name) for name in self.attributes
        ]
        read_post_control = PostReadControl(criticality=True, attrList=attributes)

        # Object already exists in the LDAP database
        if self.exists:
            deletions = [
                name
                for name, value in self.changes.items()
                if (
                    value is None
                    or value == []
                    or (isinstance(value, list) and len(value) == 1 and not value[0])
                )
                and name in self.state
            ]
            changes = {
                name: value
                for name, value in self.changes.items()
                if name not in deletions and self.state.get(name) != value
            }
            formatted_changes = python_attrs_to_ldap(changes, null_allowed=False)
            modlist = [(ldap.MOD_DELETE, name, None) for name in deletions] + [
                (ldap.MOD_REPLACE, name, values)
                for name, values in formatted_changes.items()
            ]
            _, _, _, [result] = conn.modify_ext_s(
                self.dn, modlist, serverctrls=[read_post_control]
            )

        # Object does not exist yet in the LDAP database
        else:
            changes = {
                name: value
                for name, value in {**self.state, **self.changes}.items()
                if value and value[0]
            }
            formatted_changes = python_attrs_to_ldap(changes, null_allowed=False)
            modlist = [(name, values) for name, values in formatted_changes.items()]
            _, _, _, [result] = conn.add_ext_s(
                self.dn, modlist, serverctrls=[read_post_control]
            )

        self.exists = True
        self.state = {**result.entry, **self.changes}
        self.changes = {}

    def delete(self):
        conn = Backend.instance.connection
        try:
            conn.delete_s(self.dn)
        except ldap.NO_SUCH_OBJECT:
            pass
