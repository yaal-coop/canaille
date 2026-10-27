import sqlalchemy as sa

from canaille.app import models


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


def test_group_owners_migration(app, backend, user, admin, foo_group):
    """Test that the first group owner survives a downgrade/upgrade cycle."""
    foo_group.members = [user, admin]
    foo_group.owners = [user, admin]
    backend.save(foo_group)
    user_id, group_id = user.id, foo_group.id
    backend.db_session.commit()

    backend.alembic.downgrade("-1")
    group_table = sa.table("group", sa.column("id"), sa.column("owner_id"))
    owner_id = backend.db_session.execute(
        sa.select(group_table.c.owner_id).where(group_table.c.id == group_id)
    ).scalar()
    backend.db_session.commit()
    assert owner_id == user_id

    backend.alembic.upgrade()
    backend.db_session.expire_all()
    owners = [owner.id for owner in backend.get(models.Group, id=group_id).owners]
    backend.db_session.commit()
    assert owners == [user_id]
