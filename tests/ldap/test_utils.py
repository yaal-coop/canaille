import datetime

import ldap.dn
from canaille.ldap_backend.ldapobject import LDAPObject
from canaille.ldap_backend.utils import ldap_to_python
from canaille.ldap_backend.utils import python_to_ldap
from canaille.ldap_backend.utils import Syntax
from canaille.models import Group
from canaille.models import User


def test_repr(slapd_connection, foo_group, user):
    assert repr(foo_group) == "<Group cn=['foo']>"
    assert repr(user) == "<User cn=['John (johnny) Doe']>"


def test_equality(slapd_connection, foo_group, bar_group):
    Group.ldap_object_attributes()
    assert foo_group != bar_group
    foo_group2 = Group.get(dn=foo_group.dn)
    assert foo_group == foo_group2


def test_dn_when_leading_space_in_id_attribute(slapd_connection):
    User.initialize(slapd_connection)
    user = User(
        cn=" Doe",  # leading space
        sn="Doe",
        uid="user",
        mail="john@doe.com",
    )
    user.save()

    assert ldap.dn.is_dn(user.dn)
    assert ldap.dn.dn2str(ldap.dn.str2dn(user.dn)) == user.dn
    assert user.dn == "cn=Doe,ou=users,dc=mydomain,dc=tld"

    user.delete()


def test_dn_when_ldap_special_char_in_id_attribute(slapd_connection):
    User.initialize(slapd_connection)
    user = User(
        cn="#Doe",  # special char
        sn="Doe",
        uid="user",
        mail="john@doe.com",
    )
    user.save()

    assert ldap.dn.is_dn(user.dn)
    assert ldap.dn.dn2str(ldap.dn.str2dn(user.dn)) == user.dn
    assert user.dn == "cn=\\#Doe,ou=users,dc=mydomain,dc=tld"

    user.delete()


def test_filter(slapd_connection, foo_group, bar_group):
    assert Group.filter(cn="foo") == [foo_group]
    assert Group.filter(cn="bar") == [bar_group]

    assert Group.filter(cn=["foo"]) == [foo_group]
    assert Group.filter(cn=["bar"]) == [bar_group]

    assert set(Group.filter(cn=["foo", "bar"])) == {foo_group, bar_group}


def test_ldap_to_python():
    assert (
        python_to_ldap(datetime.datetime.min, Syntax.GENERALIZED_TIME)
        == b"000001010000Z"
    )
    assert (
        python_to_ldap(datetime.datetime(2000, 1, 2, 3, 4, 5), Syntax.GENERALIZED_TIME)
        == b"20000102030405Z"
    )

    assert python_to_ldap(1337, Syntax.INTEGER) == b"1337"

    assert python_to_ldap(True, Syntax.BOOLEAN) == b"TRUE"
    assert python_to_ldap(False, Syntax.BOOLEAN) == b"FALSE"

    assert python_to_ldap("foobar", Syntax.DIRECTORY_STRING) == b"foobar"

    assert python_to_ldap(b"foobar", Syntax.JPEG) == b"foobar"


def test_python_to_ldap():
    assert ldap_to_python(
        b"20000102030405Z", Syntax.GENERALIZED_TIME
    ) == datetime.datetime(2000, 1, 2, 3, 4, 5)
    assert (
        ldap_to_python(b"000001010000Z", Syntax.GENERALIZED_TIME)
        == datetime.datetime.min
    )

    assert ldap_to_python(b"1337", Syntax.INTEGER) == 1337

    assert ldap_to_python(b"TRUE", Syntax.BOOLEAN) is True
    assert ldap_to_python(b"FALSE", Syntax.BOOLEAN) is False

    assert ldap_to_python(b"foobar", Syntax.DIRECTORY_STRING) == "foobar"

    assert ldap_to_python(b"foobar", Syntax.JPEG) == b"foobar"


def test_operational_attribute_conversion(slapd_connection):
    assert "oauthClientName" in LDAPObject.ldap_object_attributes(slapd_connection)
    assert "invalidAttribute" not in LDAPObject.ldap_object_attributes(slapd_connection)

    assert LDAPObject.ldap_attrs_to_python(
        {
            "oauthClientName": [b"foobar_name"],
            "invalidAttribute": [b"foobar"],
        }
    ) == {
        "oauthClientName": ["foobar_name"],
        "invalidAttribute": ["foobar"],
    }

    assert LDAPObject.python_attrs_to_ldap(
        {
            "oauthClientName": ["foobar_name"],
            "invalidAttribute": ["foobar"],
        }
    ) == {
        "oauthClientName": [b"foobar_name"],
        "invalidAttribute": [b"foobar"],
    }
