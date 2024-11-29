import datetime
from unittest import mock

import ldap.dn
import pytest

from canaille.app import models
from canaille.app.configuration import ConfigurationException
from canaille.app.configuration import settings_factory
from canaille.app.configuration import validate
from canaille.backends.ldap.ldapobject import LDAPObject
from canaille.backends.ldap.ldapobject import python_attrs_to_ldap
from canaille.backends.ldap.utils import Syntax
from canaille.backends.ldap.utils import ldap_to_python
from canaille.backends.ldap.utils import python_to_ldap


# TODO: tester le changement de cardinalité des attributes
def test_object_creation(app, backend):
    user = models.User(
        formatted_name="Doe",  # leading space
        family_name="Doe",
        user_name="user",
        emails=["john@doe.test"],
    )
    assert not user.exists
    backend.save(user)
    assert user.exists

    user = backend.get(models.User, id=user.id)
    assert user.exists

    backend.delete(user)


def test_repr(backend, foo_group, user):
    assert repr(foo_group) == "<Group display_name=foo>"
    assert repr(user) == "<User user_name=user>"


def test_dn_when_leading_space_in_id_attribute(testclient, backend):
    user = models.User(
        formatted_name=" Doe",  # leading space
        family_name=" Doe",
        user_name=" user",
        emails=["john@doe.test"],
    )
    backend.save(user)

    dn = user.dn
    assert dn == "uid=user,ou=users,dc=mydomain,dc=tld"
    assert ldap.dn.is_dn(dn)
    assert ldap.dn.dn2str(ldap.dn.str2dn(dn)) == dn

    assert user == backend.get(models.User, user.user_name)
    assert user == backend.get(models.User, user_name=user.user_name)
    assert user == backend.get(models.User, dn)

    backend.delete(user)


def test_special_chars_in_rdn(testclient, backend):
    user = models.User(
        formatted_name="#Doe",
        family_name="#Doe",
        user_name="#user",  # special char
        emails=["john@doe.test"],
    )
    backend.save(user)

    dn = user.dn
    assert ldap.dn.is_dn(dn)
    assert ldap.dn.dn2str(ldap.dn.str2dn(dn)) == dn
    assert dn == "uid=\\#user,ou=users,dc=mydomain,dc=tld"

    assert user == backend.get(models.User, user.user_name)
    assert user == backend.get(models.User, user_name=user.user_name)
    assert user == backend.get(models.User, dn)

    backend.delete(user)


def test_filter(backend, foo_group, bar_group):
    assert backend.query(models.Group, display_name="foo") == [foo_group]
    assert backend.query(models.Group, display_name="bar") == [bar_group]

    assert backend.query(models.Group, display_name="foo") != 3

    assert backend.query(models.Group, display_name=["foo"]) == [foo_group]
    assert backend.query(models.Group, display_name=["bar"]) == [bar_group]

    assert set(backend.query(models.Group, display_name=["foo", "bar"])) == {
        foo_group,
        bar_group,
    }


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


def test_operational_attribute_conversion(backend):
    assert "oauthClientName" in LDAPObject.ldap_object_attributes(backend.connection)
    assert "invalidAttribute" not in LDAPObject.ldap_object_attributes(
        backend.connection
    )

    assert python_attrs_to_ldap(
        {
            "oauthClientName": ["foobar_name"],
            "invalidAttribute": ["foobar"],
        }
    ) == {
        "oauthClientName": [b"foobar_name"],
        "invalidAttribute": [b"foobar"],
    }


def test_ldap_connection_no_remote(testclient, configuration):
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()
    validate(config_dict)


def test_ldap_connection_remote(testclient, configuration, backend, mock_smpp):
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()
    validate(config_dict, validate_remote=True)


def test_ldap_connection_remote_ldap_unreachable(testclient, configuration):
    configuration["CANAILLE_LDAP"]["URI"] = "ldap://invalid-ldap.com"
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()

    with pytest.raises(
        ConfigurationException,
        match=r"Could not connect to the LDAP server",
    ):
        validate(config_dict, validate_remote=True)


def test_ldap_connection_remote_ldap_wrong_credentials(testclient, configuration):
    configuration["CANAILLE_LDAP"]["BIND_PW"] = "invalid-password"
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()

    with pytest.raises(
        ConfigurationException,
        match=r"LDAP authentication failed with user",
    ):
        validate(config_dict, validate_remote=True)


def test_ldap_cannot_create_users(testclient, configuration, backend):
    from canaille.core.models import User

    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()

    def fake_init(*args, **kwarg):
        raise ldap.INSUFFICIENT_ACCESS

    with mock.patch.object(User, "__init__", fake_init):
        with pytest.raises(
            ConfigurationException,
            match=r"cannot create users at",
        ):
            validate(config_dict, validate_remote=True)


def test_ldap_cannot_create_groups(testclient, configuration, backend):
    from canaille.core.models import Group

    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()

    def fake_init(*args, **kwarg):
        raise ldap.INSUFFICIENT_ACCESS

    with mock.patch.object(Group, "__init__", fake_init):
        with pytest.raises(
            ConfigurationException,
            match=r"cannot create groups at",
        ):
            validate(config_dict, validate_remote=True)


def test_login_placeholder(testclient):
    testclient.app.config["CANAILLE_LDAP"]["USER_FILTER"] = "(uid={{ login }})"
    placeholder = testclient.get("/login").form["login"].attrs["placeholder"]
    assert placeholder == "jdoe"

    testclient.app.config["CANAILLE_LDAP"]["USER_FILTER"] = "(cn={{ login }})"
    placeholder = testclient.get("/login").form["login"].attrs["placeholder"]
    assert placeholder == "John Doe"

    testclient.app.config["CANAILLE_LDAP"]["USER_FILTER"] = "(mail={{ login }})"
    placeholder = testclient.get("/login").form["login"].attrs["placeholder"]
    assert placeholder == "john.doe@example.com"

    testclient.app.config["CANAILLE_LDAP"]["USER_FILTER"] = (
        "(|(uid={{ login }})(mail={{ login }}))"
    )
    placeholder = testclient.get("/login").form["login"].attrs["placeholder"]
    assert placeholder == "jdoe or john.doe@example.com"
