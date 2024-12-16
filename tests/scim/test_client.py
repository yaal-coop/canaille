import logging

from canaille.app import models


def test_scim_client_user_save_and_delete(
    scim_server, scim_client_for_preconsented_client, backend, user
):
    User = scim_client_for_preconsented_client.get_resource_model("User")

    response = scim_client_for_preconsented_client.query(User)
    assert not response.resources

    backend.save(user)
    response = scim_client_for_preconsented_client.query(User)
    assert len(response.resources) == 1
    assert response.resources[0].user_name == "user"

    backend.delete(user)
    response = scim_client_for_preconsented_client.query(User)
    assert not response.resources


def test_scim_client_group_save_and_delete(
    scim_server, scim_client_for_preconsented_client, backend, user
):
    Group = scim_client_for_preconsented_client.get_resource_model("Group")

    response = scim_client_for_preconsented_client.query(Group)
    assert not response.resources

    group = models.Group(
        members=[user],
        display_name="foobar",
    )
    backend.save(group)

    response = scim_client_for_preconsented_client.query(Group)
    assert len(response.resources) == 1
    retrieved_group = response.resources[0]
    assert retrieved_group.display_name == "foobar"
    assert retrieved_group.members[0].value == user.id

    backend.delete(group)
    response = scim_client_for_preconsented_client.query(Group)
    assert not response.resources


def test_scim_client_change_user_groups_also_updates_group_members(
    testclient,
    scim_server,
    scim_client_for_preconsented_client,
    backend,
    user,
    logged_admin,
    bar_group,
):
    Group = scim_client_for_preconsented_client.get_resource_model("Group")

    res = testclient.get("/profile/user/settings", status=200)
    res.form["groups"] = [bar_group.id]
    res = res.form.submit(name="action", value="edit-settings")

    response = scim_client_for_preconsented_client.query(Group)
    assert len(response.resources) == 1
    retrieved_bar_group = response.resources[0]
    assert retrieved_bar_group.display_name == "bar"
    assert len(retrieved_bar_group.members) == 2
    assert retrieved_bar_group.members[0].value == logged_admin.id
    assert retrieved_bar_group.members[1].value == user.id

    response = scim_client_for_preconsented_client.query(Group)

    res = testclient.get("/profile/user/settings", status=200)
    res.form["groups"] = []
    res = res.form.submit(name="action", value="edit-settings")

    response = scim_client_for_preconsented_client.query(Group)

    assert len(response.resources) == 1
    retrieved_bar_group = response.resources[0]
    assert retrieved_bar_group.display_name == "bar"
    assert len(retrieved_bar_group.members) == 1
    assert retrieved_bar_group.members[0].value == logged_admin.id


def test_scim_client_user_creation_and_deletion_also_updates_their_groups(
    testclient,
    scim_server,
    scim_client_for_preconsented_client,
    backend,
    foo_group,
    bar_group,
    user,
    admin,
    logged_admin,
):
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    Group = scim_client_for_preconsented_client.get_resource_model("Group")
    response = scim_client_for_preconsented_client.query(Group)

    assert len(response.resources) == 2
    retrieved_foo_group = response.resources[0]
    assert retrieved_foo_group.display_name == "foo"
    assert len(retrieved_foo_group.members) == 1
    assert retrieved_foo_group.members[0].value == user.id
    retrieved_bar_group = response.resources[1]
    assert retrieved_bar_group.display_name == "bar"
    assert len(retrieved_bar_group.members) == 1
    assert retrieved_bar_group.members[0].value == admin.id

    assert not backend.query(models.User, user_name="newuser")
    res = testclient.get("/profile", status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "i'm a little pea"
    res.form["password2"] = "i'm a little pea"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.test"
    res.form["groups"] = [foo_group.id, bar_group.id]
    res = res.form.submit(name="action", value="create-profile", status=302)
    assert ("success", "User account creation succeeded.") in res.flashes

    newuser = backend.get(models.User, user_name="newuser")
    assert newuser

    response = scim_client_for_preconsented_client.query(Group)
    assert len(response.resources) == 2
    retrieved_foo_group = response.resources[0]
    assert retrieved_foo_group.display_name == "foo"
    assert len(retrieved_foo_group.members) == 2
    assert retrieved_foo_group.members[0].value == user.id
    assert retrieved_foo_group.members[1].value == newuser.id
    retrieved_bar_group = response.resources[1]
    assert retrieved_bar_group.display_name == "bar"
    assert len(retrieved_bar_group.members) == 2
    assert retrieved_bar_group.members[0].value == admin.id
    assert retrieved_bar_group.members[1].value == newuser.id

    backend.delete(newuser)

    response = scim_client_for_preconsented_client.query(Group)
    assert len(response.resources) == 2
    retrieved_foo_group = response.resources[0]
    assert retrieved_foo_group.display_name == "foo"
    assert len(retrieved_foo_group.members) == 1
    assert retrieved_foo_group.members[0].value == user.id
    retrieved_bar_group = response.resources[1]
    assert retrieved_bar_group.display_name == "bar"
    assert len(retrieved_bar_group.members) == 1
    assert retrieved_bar_group.members[0].value == admin.id


def test_client_doesnt_support_scim(backend, user, consent, caplog):
    backend.save(user)
    assert (
        "canaille",
        logging.INFO,
        "SCIM protocol not supported by client Client",
    ) in caplog.record_tuples
