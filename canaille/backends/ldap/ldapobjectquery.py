import itertools
from collections.abc import Iterable


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
        from .ldapobject import LDAPObject
        from .ldapobject import LDAPObjectMetaclass

        if klass == LDAPObject:
            models = [
                LDAPObjectMetaclass.ldap_to_python_class[oc.decode()]
                for oc in object_classes
                if oc.decode() in LDAPObjectMetaclass.ldap_to_python_class
            ]
            return models[0]
        return klass
