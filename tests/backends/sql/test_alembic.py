def test_migrations(app, backend):
    """Test downgrading back to the first revision, and then re-apply all migrations."""
    backend.alembic.downgrade("base")
    backend.alembic.upgrade()
