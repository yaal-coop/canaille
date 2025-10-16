from canaille.app import models


def test_user_has_password(testclient, backend):
    """Test that the has_password method correctly identifies whether a user has a password set."""
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
    """Test that password setting and checking works correctly."""
    assert not backend.check_user_password(user, "something else")[0]
    assert backend.check_user_password(user, "correct horse battery staple")[0]

    backend.set_user_password(user, "something else")

    assert backend.check_user_password(user, "something else")[0]
    assert not backend.check_user_password(user, "correct horse battery staple")[0]
