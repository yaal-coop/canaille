Databases
#########

Canaille can read and save data in different databases.
This section presents the different database backends and their specificities:

.. toctree::
   :maxdepth: 2

   memory
   sql
   ldap

Dump and restore
================

Backups
-------

The :ref:`cli_dump` and :ref:`cli_restore` commands can be used to dump all the Canaille objects, or load them in the current database.
Those commands can be used for backuping Canaille data.

.. _database_migration:

Migration
---------

The dump format is the same whatever database backend is used, and thus it can be used to migrate from a database backend to another.
To achieve a migration, you need to have two configuration files prepared for the source database and the destination database.
For instance, if you want to migrate from a LDAP database to a SQL database, you can execute something like this:

.. code-block:: console
    :caption: Migrating data from a LDAP directory to a SQL database

    $ env CANAILLE_CONFIG=sql-config.toml canaille install
    $ env CANAILLE_CONFIG=ldap -config.toml canaille dump | env CANAILLE_CONFIG=sql-config.toml canaille restore
