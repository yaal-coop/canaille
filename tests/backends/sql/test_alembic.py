def test_migrations(app, backend):
    """Test downgrading back to the first revision, and then re-apply all migrations."""
    backend.alembic.downgrade("base")
    backend.alembic.upgrade()
    backend.alembic.downgrade("base")
    backend.alembic.upgrade()


def test_migrations_with_data(app, backend, user, foo_group):
    """Test that data survives a downgrade/upgrade cycle."""
    script = backend.alembic.script_directory
    revisions = list(script.walk_revisions("base", "head"))

    # Store original data for comparison
    original_user_name = user.user_name
    original_group_name = foo_group.display_name
    original_group_members = len(foo_group.members)

    # IMPORTANT: Close any open transaction before running migrations
    # Reading data above may have started an implicit transaction that holds locks
    backend.db_session.commit()

    # Downgrade to first revision (preserves tables and data)
    steps_to_first = len(revisions) - 1
    backend.alembic.downgrade(f"-{steps_to_first}")

    # Upgrade back to head
    backend.alembic.upgrade()

    # Verify data integrity
    backend.reload(user)
    backend.reload(foo_group)
    assert user.user_name == original_user_name
    assert foo_group.display_name == original_group_name
    assert len(foo_group.members) == original_group_members
