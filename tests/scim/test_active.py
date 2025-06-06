def test_set_active_to_false_locks_user_and_vice_versa(scim_client, user, backend):
    assert user.lock_date is None

    scim_client.discover()
    User = scim_client.get_resource_model("User")

    users = scim_client.query(User)
    distant_scim_user = next(
        (myuser for myuser in users.resources if myuser.user_name == user.user_name),
        None,
    )

    distant_scim_user.active = False
    scim_client.replace(distant_scim_user)
    backend.reload(user)
    assert user.lock_date
    assert user.locked

    distant_scim_user.active = True
    scim_client.replace(distant_scim_user)
    backend.reload(user)
    assert user.lock_date is None
    assert not user.locked

    # "None" active parameter shouldn't change the state
    distant_scim_user.active = None
    scim_client.replace(distant_scim_user)
    backend.reload(user)
    assert user.lock_date is None
    assert not user.locked
