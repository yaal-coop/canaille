from canaille.app import models


def test_user_get_user_from_login(testclient, user, backend):
    assert backend.get_user_from_login(login="invalid") is None
    assert backend.get_user_from_login(login="user") == user


def test_user_has_password(testclient, backend):
    user = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.test"],
    )
    backend.save(user)

    assert user.password is None
    assert not user.has_password()

    user.password = "foobar"
    backend.save(user)

    assert user.password is not None
    assert user.has_password()

    backend.delete(user)


def test_user_set_and_check_password(testclient, user, backend):
    assert not backend.check_user_password(user, "something else")[0]
    assert backend.check_user_password(user, "correct horse battery staple")[0]

    backend.set_user_password(user, "something else")

    assert backend.check_user_password(user, "something else")[0]
    assert not backend.check_user_password(user, "correct horse battery staple")[0]
