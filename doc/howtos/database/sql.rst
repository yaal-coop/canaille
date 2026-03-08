SQL
===

Canaille can use any database supported by `SQLAlchemy <https://www.sqlalchemy.org/>`_, such as
sqlite or postgresql.

Configuration
-------------

It is used when the ``CANAILLE_SQL`` configuration parameter is defined. For instance:

.. code-block:: toml
    :caption: config.toml

    [CANAILLE_SQL]
    SQL_DATABASE_URI = "postgresql://user:password@localhost/database"

You can find more details on the SQL configuration in the :class:`dedicated section <canaille.backends.sql.configuration.SQLSettings>`.

Migrations
----------

By default, migrations are applied when you run the web application.
You can disable this behavior with the :attr:`~canaille.backends.sql.configuration.SQLSettings.AUTO_MIGRATE` setting.
Migrations are not automatically applied with the use of the CLI though.

Migrations are done with :doc:`flask-alembic <flask-alembic:use>`, that provides a dedicated CLI to manually tune migrations.
You can check the :doc:`flask-alembic documentation <flask-alembic:index>` and the ``canaille db`` command line if you are in trouble.
