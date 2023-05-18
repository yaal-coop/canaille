from canaille.core.models import User


def test_user_get_from_login(testclient, user, slapd_connection):
    assert User.get_from_login(login="invalid") is None
    assert User.get_from_login(login="user") == user


def test_user_has_password(testclient, slapd_connection):
    u = User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        email="john@doe.com",
    )
    u.save()

    assert not u.has_password()

    u.password = "foobar"
    u.save()

    assert u.has_password()

    u.delete()


def test_user_set_and_check_password(testclient, user, slapd_connection):
    assert not user.check_password("something else")
    assert user.check_password("correct horse battery staple")

    user.set_password("something else")

    assert user.check_password("something else")
    assert not user.check_password("correct horse battery staple")
