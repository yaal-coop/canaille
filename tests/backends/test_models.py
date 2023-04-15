from canaille.app import models


def test_model_comparison(testclient, backend):
    foo1 = models.User(
        user_name="foo",
        family_name="foo",
        formatted_name="foo",
    )
    foo1.save()
    bar = models.User(
        user_name="bar",
        family_name="bar",
        formatted_name="bar",
    )
    bar.save()
    foo2 = models.User.get(id=foo1.id)

    assert foo1 == foo2
    assert foo1 != bar

    foo1.delete()
    bar.delete()


def test_model_lifecycle(testclient, backend):
    user = models.User(
        user_name="user_name",
        family_name="family_name",
        formatted_name="formatted_name",
    )

    assert not models.User.query()
    assert not models.User.query(id=user.id)
    assert not models.User.query(id="invalid")
    assert not models.User.get(id=user.id)

    user.save()

    assert models.User.query() == [user]
    assert models.User.query(id=user.id) == [user]
    assert not models.User.query(id="invalid")
    assert models.User.get(id=user.id) == user

    user.family_name = "new_family_name"

    assert user.family_name == ["new_family_name"]

    user.reload()

    assert user.family_name == ["family_name"]

    user.delete()

    assert not models.User.query(id=user.id)
    assert not models.User.get(id=user.id)


def test_model_attribute_edition(testclient, backend):
    user = models.User(
        user_name="user_name",
        family_name="family_name",
        formatted_name="formatted_name",
        display_name="display_name",
        emails=["email1@user.com", "email2@user.com"],
    )
    user.save()

    assert user.user_name == ["user_name"]
    assert user.family_name == ["family_name"]
    assert user.emails == ["email1@user.com", "email2@user.com"]

    user = models.User.get(id=user.id)
    assert user.user_name == ["user_name"]
    assert user.family_name == ["family_name"]
    assert user.emails == ["email1@user.com", "email2@user.com"]

    user.family_name = ["new_family_name"]
    user.emails = ["email1@user.com"]
    user.save()

    assert user.family_name == ["new_family_name"]
    assert user.emails == ["email1@user.com"]

    user = models.User.get(id=user.id)
    assert user.family_name == ["new_family_name"]
    assert user.emails == ["email1@user.com"]

    user.display_name = [""]
    user.save()

    assert not user.display_name

    user.delete()


def test_model_indexation(testclient, backend):
    user = models.User(
        user_name="user_name",
        family_name="family_name",
        formatted_name="formatted_name",
        emails=["email1@user.com", "email2@user.com"],
    )
    user.save()

    assert models.User.get(family_name="family_name") == user
    assert not models.User.get(family_name="new_family_name")
    assert models.User.get(emails="email1@user.com") == user
    assert models.User.get(emails="email2@user.com") == user
    assert not models.User.get(emails="email3@user.com")

    user.family_name = "new_family_name"
    user.emails = ["email2@user.com"]

    assert models.User.get(family_name="family_name") != user
    assert not models.User.get(family_name="new_family_name")
    assert models.User.get(emails="email1@user.com") != user
    assert models.User.get(emails="email2@user.com") != user
    assert not models.User.get(emails="email3@user.com")

    user.save()

    assert not models.User.get(family_name="family_name")
    assert models.User.get(family_name="new_family_name") == user
    assert not models.User.get(emails="email1@user.com")
    assert models.User.get(emails="email2@user.com") == user
    assert not models.User.get(emails="email3@user.com")

    user.delete()

    assert not models.User.get(family_name="family_name")
    assert not models.User.get(family_name="new_family_name")
    assert not models.User.get(emails="email1@user.com")
    assert not models.User.get(emails="email2@user.com")
    assert not models.User.get(emails="email3@user.com")


def test_fuzzy(user, moderator, admin, backend):
    assert set(models.User.query()) == {user, moderator, admin}
    assert set(models.User.fuzzy("Jack")) == {moderator}
    assert set(models.User.fuzzy("Jack", ["formatted_name"])) == {moderator}
    assert set(models.User.fuzzy("Jack", ["user_name"])) == set()
    assert set(models.User.fuzzy("Jack", ["user_name", "formatted_name"])) == {
        moderator
    }
    assert set(models.User.fuzzy("moderator")) == {moderator}
    assert set(models.User.fuzzy("oderat")) == {moderator}
    assert set(models.User.fuzzy("oDeRat")) == {moderator}
    assert set(models.User.fuzzy("ack")) == {moderator}


# def test_model_references(user, admin, foo_group, bar_group):
def test_model_references(testclient, user, foo_group, admin, bar_group, backend):
    # assert foo_group.members == [user]
    # assert user.groups == [foo_group]
    # assert foo_group in models.Group.query(members=user)
    assert user in models.User.query(groups=foo_group)

    assert user not in bar_group.members
    assert bar_group not in user.groups
    user.groups = user.groups + [bar_group]
    user.save()
    bar_group.reload()

    assert user in bar_group.members
    assert bar_group in user.groups

    bar_group.members = [admin]
    bar_group.save()
    user.reload()

    assert user not in bar_group.members
    assert bar_group not in user.groups


def test_model_references_set_unsaved_object(
    testclient, logged_moderator, user, backend
):
    group = models.Group(members=[user], display_name="foo")
    group.save()
    user.reload()  # LDAP groups can be inconsistent by containing members which doesn't exist

    non_existent_user = models.User(
        formatted_name="foo", family_name="bar", user_name="baz"
    )
    group.members = group.members + [non_existent_user]
    assert group.members == [user, non_existent_user]

    group.save()
    assert group.members == [user, non_existent_user]

    group.reload()
    assert group.members == [user]

    testclient.get("/groups/foo", status=200)

    group.delete()
