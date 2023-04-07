import datetime

import ldap.dn
from canaille.ldap_backend.backend import setup_ldap_models
from canaille.ldap_backend.ldapobject import LDAPObject
from canaille.ldap_backend.ldapobject import python_attrs_to_ldap
from canaille.ldap_backend.utils import ldap_to_python
from canaille.ldap_backend.utils import python_to_ldap
from canaille.ldap_backend.utils import Syntax
from canaille.models import Group
from canaille.models import User


def test_object_creation(slapd_connection):
    User.initialize(slapd_connection)
    user = User(
        formatted_name="Doe",  # leading space
        family_name="Doe",
        user_name="user",
        email="john@doe.com",
    )
    assert not user.exists
    user.save()
    assert user.exists

    user = User.get(id=user.id)
    assert user.exists

    user.delete()


def test_repr(slapd_connection, foo_group, user):
    assert repr(foo_group) == "<Group display_name=foo>"
    assert repr(user) == "<User formatted_name=John (johnny) Doe>"


def test_equality(slapd_connection, foo_group, bar_group):
    assert foo_group != bar_group
    foo_group2 = Group.get(id=foo_group.id)
    assert foo_group == foo_group2


def test_dn_when_leading_space_in_id_attribute(slapd_connection):
    User.initialize(slapd_connection)
    user = User(
        formatted_name=" Doe",  # leading space
        family_name="Doe",
        user_name="user",
        email="john@doe.com",
    )
    user.save()

    assert ldap.dn.is_dn(user.dn)
    assert ldap.dn.dn2str(ldap.dn.str2dn(user.dn)) == user.dn
    assert user.dn == "cn=Doe,ou=users,dc=mydomain,dc=tld"

    user.delete()


def test_dn_when_ldap_special_char_in_id_attribute(slapd_connection):
    User.initialize(slapd_connection)
    user = User(
        formatted_name="#Doe",  # special char
        family_name="Doe",
        user_name="user",
        email="john@doe.com",
    )
    user.save()

    assert ldap.dn.is_dn(user.dn)
    assert ldap.dn.dn2str(ldap.dn.str2dn(user.dn)) == user.dn
    assert user.dn == "cn=\\#Doe,ou=users,dc=mydomain,dc=tld"

    user.delete()


def test_filter(slapd_connection, foo_group, bar_group):
    assert Group.query(display_name="foo") == [foo_group]
    assert Group.query(display_name="bar") == [bar_group]

    assert Group.query(display_name="foo") != 3

    assert Group.query(display_name=["foo"]) == [foo_group]
    assert Group.query(display_name=["bar"]) == [bar_group]

    assert set(Group.query(display_name=["foo", "bar"])) == {foo_group, bar_group}


def test_fuzzy(slapd_connection, user, moderator, admin):
    assert set(User.query()) == {user, moderator, admin}
    assert set(User.fuzzy("Jack")) == {moderator}
    assert set(User.fuzzy("Jack", ["formatted_name"])) == {moderator}
    assert set(User.fuzzy("Jack", ["user_name"])) == set()
    assert set(User.fuzzy("Jack", ["user_name", "formatted_name"])) == {moderator}
    assert set(User.fuzzy("moderator")) == {moderator}
    assert set(User.fuzzy("oderat")) == {moderator}
    assert set(User.fuzzy("oDeRat")) == {moderator}
    assert set(User.fuzzy("ack")) == {moderator}


def test_ldap_to_python():
    assert (
        python_to_ldap(
            datetime.datetime(2000, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc),
            Syntax.GENERALIZED_TIME,
        )
        == b"20000102030405Z"
    )
    assert (
        python_to_ldap(
            datetime.datetime(
                2000,
                1,
                2,
                3,
                4,
                5,
                tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=79200)),
            ),
            Syntax.GENERALIZED_TIME,
        )
        == b"20000102030405-0200"
    )
    assert (
        python_to_ldap(datetime.datetime.min, Syntax.GENERALIZED_TIME)
        == b"000001010000Z"
    )

    assert python_to_ldap(1337, Syntax.INTEGER) == b"1337"

    assert python_to_ldap(True, Syntax.BOOLEAN) == b"TRUE"
    assert python_to_ldap(False, Syntax.BOOLEAN) == b"FALSE"

    assert python_to_ldap("foobar", Syntax.DIRECTORY_STRING) == b"foobar"

    assert python_to_ldap(b"foobar", Syntax.JPEG) == b"foobar"


def test_python_to_ldap():
    assert ldap_to_python(
        b"20000102030405Z", Syntax.GENERALIZED_TIME
    ) == datetime.datetime(2000, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
    assert ldap_to_python(
        b"20000102030405-0200", Syntax.GENERALIZED_TIME
    ) == datetime.datetime(
        2000,
        1,
        2,
        3,
        4,
        5,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=79200)),
    )
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

    assert python_attrs_to_ldap(
        {
            "oauthClientName": ["foobar_name"],
            "invalidAttribute": ["foobar"],
        }
    ) == {
        "oauthClientName": [b"foobar_name"],
        "invalidAttribute": [b"foobar"],
    }


def test_guess_object_from_dn(slapd_connection, testclient, foo_group):
    foo_group.member = [foo_group]
    foo_group.save()
    g = LDAPObject.get(id=foo_group.dn)
    assert isinstance(g, Group)
    assert g == foo_group
    assert g.cn == foo_group.cn

    ou = LDAPObject.get(id=f"{Group.base},{Group.root_dn}")
    assert isinstance(g, LDAPObject)


def test_object_class_update(slapd_connection, testclient):
    testclient.app.config["LDAP"]["USER_CLASS"] = ["inetOrgPerson"]
    setup_ldap_models(testclient.app.config)

    user1 = User(cn="foo1", sn="bar1")
    user1.save()

    assert user1.objectClass == ["inetOrgPerson"]
    assert User.get(id=user1.id).objectClass == ["inetOrgPerson"]

    testclient.app.config["LDAP"]["USER_CLASS"] = ["inetOrgPerson", "extensibleObject"]
    setup_ldap_models(testclient.app.config)

    user2 = User(cn="foo2", sn="bar2")
    user2.save()

    assert user2.objectClass == ["inetOrgPerson", "extensibleObject"]
    assert User.get(id=user2.id).objectClass == ["inetOrgPerson", "extensibleObject"]

    user1 = User.get(id=user1.id)
    assert user1.objectClass == ["inetOrgPerson"]

    user1.save()
    assert user1.objectClass == ["inetOrgPerson", "extensibleObject"]
    assert User.get(id=user1.id).objectClass == ["inetOrgPerson", "extensibleObject"]
