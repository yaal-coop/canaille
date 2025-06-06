def test_set_active_to_false_locks_user_and_vice_versa(scim_client, scim_user, backend):
    assert scim_user.lock_date is None

    scim_client.discover()
    User = scim_client.get_resource_model("User")

    users = scim_client.query(User)
    distant_scim_user = next(
        (
            myuser
            for myuser in users.resources
            if myuser.user_name == scim_user.user_name
        ),
        None,
    )

    distant_scim_user.active = False
    scim_client.replace(distant_scim_user)
    backend.reload(scim_user)
    assert scim_user.lock_date
    assert scim_user.locked

    distant_scim_user.active = True
    scim_client.replace(distant_scim_user)
    backend.reload(scim_user)
    assert scim_user.lock_date is None
    assert not scim_user.locked
    # "None" active parameter shouldn't change the state
    distant_scim_user.active = None
    scim_client.replace(distant_scim_user)
    backend.reload(scim_user)
    assert scim_user.lock_date is None
    assert not scim_user.locked
