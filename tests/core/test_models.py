import pytest

from canaille.app import models
from canaille.core.models import Group
from canaille.core.models import User


def test_required_methods(testclient):
    with pytest.raises(NotImplementedError):
        User.get_from_login()

    user = User()

    with pytest.raises(NotImplementedError):
        user.check_password("password")

    with pytest.raises(NotImplementedError):
        user.set_password("password")

    Group()


def test_user_get_from_login(testclient, user, backend):
    assert models.User.get_from_login(login="invalid") is None
    assert models.User.get_from_login(login="user") == user


def test_user_has_password(testclient, backend):
    user = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.com"],
    )
    user.save()

    assert user.password is None
    assert not user.has_password()

    user.password = "foobar"
    user.save()

    assert user.password is not None
    assert user.has_password()

    user.delete()


def test_user_set_and_check_password(testclient, user, backend):
    assert not user.check_password("something else")[0]
    assert user.check_password("correct horse battery staple")[0]

    user.set_password("something else")

    assert user.check_password("something else")[0]
    assert not user.check_password("correct horse battery staple")[0]
