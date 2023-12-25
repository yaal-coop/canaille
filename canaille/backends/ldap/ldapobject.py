import itertools
from collections.abc import Iterable

import ldap.dn
import ldap.filter
from canaille.backends.models import Model

from .backend import Backend
from .utils import cardinalize_attribute
from .utils import ldap_to_python
from .utils import listify
from .utils import python_to_ldap


def python_attrs_to_ldap(attrs, encode=True, null_allowed=True):
    formatted_attrs = {
        name: [
            python_to_ldap(value, attribute_ldap_syntax(name), encode=encode)
            for value in listify(values)
        ]
        for name, values in attrs.items()
    }
    if not null_allowed:
        formatted_attrs = {
            key: [value for value in values if value]
            for key, values in formatted_attrs.items()
            if values
        }
    return formatted_attrs


def attribute_ldap_syntax(attribute_name):
    ldap_attrs = LDAPObject.ldap_object_attributes()
    if attribute_name not in ldap_attrs:
        return None

    if ldap_attrs[attribute_name].syntax:
        return ldap_attrs[attribute_name].syntax

    return attribute_ldap_syntax(ldap_attrs[attribute_name].sup[0])


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


class LDAPObjectQuery:
    def __init__(self, klass, items):
        self.klass = klass
        self.items = items

    def __len__(self):
        return len(self.items)

    def __getitem__(self, item):
        if isinstance(item, slice):
            return (self.decorate(obj[1]) for obj in self.items[item])

        return self.decorate(self.items[item][1])

    def __iter__(self):
        return (self.decorate(obj[1]) for obj in self.items)

    def __eq__(self, other):
        if isinstance(other, Iterable):
            return all(
                a == b
                for a, b in itertools.zip_longest(
                    iter(self), iter(other), fillvalue=object()
                )
            )
        return super().__eq__(other)

    def __bool__(self):
        return bool(self.items)

    def decorate(self, args):
        klass = self.guess_class(self.klass, args["objectClass"])
        obj = klass()
        obj.state = args
        obj.exists = True
        return obj

    def guess_class(self, klass, object_classes):
        if klass == LDAPObject:
            for oc in object_classes:
                if oc.decode() in LDAPObjectMetaclass.ldap_to_python_class:
                    return LDAPObjectMetaclass.ldap_to_python_class[oc.decode()]
        return klass


class LDAPObject(Model, metaclass=LDAPObjectMetaclass):
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

    def __html__(self):
        return self.id

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

    def __getattr__(self, name):
        if name not in self.attributes:
            return super().__getattribute__(name)

        ldap_name = self.python_attribute_to_ldap(name)

        if ldap_name == "dn":
            return self.dn_for(self.rdn_value)

        python_single_value = "List" not in str(self.__annotations__[name])
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
        conn = Backend.get().connection
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

        conn = Backend.get().connection

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

        conn = Backend.get().connection

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
    def get(cls, id=None, filter=None, **kwargs):
        try:
            return cls.query(id, filter, **kwargs)[0]
        except (IndexError, ldap.NO_SUCH_OBJECT):
            return None

    @classmethod
    def query(cls, id=None, filter=None, **kwargs):
        conn = Backend.get().connection

        base = id or kwargs.get("id")
        if base is None:
            base = f"{cls.base},{cls.root_dn}"
        elif "=" not in base:
            base = ldap.dn.escape_dn_chars(base)
            base = f"{cls.rdn_attribute}={base},{cls.base},{cls.root_dn}"

        class_filter = (
            "".join([f"(objectClass={oc})" for oc in cls.ldap_object_class])
            if getattr(cls, "ldap_object_class")
            else ""
        )
        if class_filter:
            class_filter = f"(|{class_filter})"
        arg_filter = ""
        kwargs = python_attrs_to_ldap(
            {
                cls.python_attribute_to_ldap(name): values
                for name, values in kwargs.items()
            },
            encode=False,
        )
        for key, value in kwargs.items():
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
        base = base or f"{cls.base},{cls.root_dn}"
        try:
            result = conn.search_s(
                base, ldap.SCOPE_SUBTREE, ldapfilter or None, ["+", "*"]
            )
        except ldap.NO_SUCH_OBJECT:
            result = []
        return LDAPObjectQuery(cls, result)

    @classmethod
    def fuzzy(cls, query, attributes=None, **kwargs):
        query = ldap.filter.escape_filter_chars(query)
        attributes = attributes or cls.may() + cls.must()
        attributes = [cls.python_attribute_to_ldap(name) for name in attributes]
        filter = (
            "(|" + "".join(f"({attribute}=*{query}*)" for attribute in attributes) + ")"
        )
        return cls.query(filter=filter, **kwargs)

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
        conn = Backend.get().connection
        result = conn.search_s(self.id, ldap.SCOPE_SUBTREE, None, ["+", "*"])
        self.changes = {}
        self.state = result[0][1]

    def save(self):
        conn = Backend.get().connection

        self.set_ldap_attribute("objectClass", self.ldap_object_class)

        # Object already exists in the LDAP database
        if self.exists:
            deletions = [
                name
                for name, value in self.changes.items()
                if (
                    value is None
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
            conn.modify_s(self.id, modlist)

        # Object does not exist yet in the LDAP database
        else:
            changes = {
                name: value
                for name, value in {**self.state, **self.changes}.items()
                if value and value[0]
            }
            formatted_changes = python_attrs_to_ldap(changes, null_allowed=False)
            attributes = [(name, values) for name, values in formatted_changes.items()]
            conn.add_s(self.id, attributes)

        self.exists = True
        self.state = {**self.state, **self.changes}
        self.changes = {}

    def delete(self):
        conn = Backend.get().connection
        conn.delete_s(self.id)
