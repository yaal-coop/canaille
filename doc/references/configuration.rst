Configuration
#############

Load the configuration
======================

Canaille can be configured either by a environment variables, environment file, or by a configuration file.

Configuration file
~~~~~~~~~~~~~~~~~~

.. envvar:: CONFIG

    The configuration can be written in `toml` configuration file which path is passed in the :envvar:`CONFIG` environment variable.

.. code-block:: toml
    :caption: config.toml

    SECRET_KEY = "very-secret"

    [CANAILLE]
    NAME = "My organization"

    [CANAILLE_SQL]
    DATABASE_URI = "postgresql://user:password@localhost/database"
    ...

You can have a look at the :ref:`example file <references/configuration:Example file>` for inspiration.

Environment variables
~~~~~~~~~~~~~~~~~~~~~

In addition, parameters that have not been set in the configuration file can be read from environment variables.
The way environment variables are parsed can be read from the `pydantic-settings documentation <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#parsing-environment-variable-values>`_.

.. tip::

   For environment vars, the separator between sections and variables is a double underscore: ``__``.
   For instance, the ``NAME`` var in the ``CANAILLE`` section shown above is ``CANAILLE__NAME``.

Environment file
~~~~~~~~~~~~~~~~

Any environment variable can also be written in an environment file, which path should be passed in the ``ENV_FILE`` environment variable.
For instance, set ``ENV_FILE=.env`` to load a ``.env`` file.

.. code-block:: bash
    :caption: .env

    SECRET_KEY="very-secret"
    CANAILLE__NAME="My organization"
    CANAILLE_SQL__DATABASE_URI="postgresql://user:password@localhost/database"

.. TODO: Uncomment this when pydantic-settings implements nested secrets directories
   https://github.com/pydantic/pydantic-settings/issues/154

    Secret parameters
    =================

        A :envvar:`SECRETS_DIR` environment variable can be passed as an environment variable, being a path to a directory in which are stored files named after the configuration settings.

        For instance, you can set ``SECRETS_DIR=/run/secrets`` and put your secret key in the file ``/run/secrets/SECRET_KEY``.

Configuration methods priority
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If a same configuration option is defined by different ways, here is how Canaille will choose which one to use:

- environment vars have priority over the environment file and the configuration file;
- environment file will have priority over the configuration file.

Parameters
==========

.. autopydantic_settings:: canaille.app.configuration.RootSettings

.. autopydantic_settings:: canaille.core.configuration.CoreSettings
.. autopydantic_settings:: canaille.core.configuration.SMTPSettings
.. autopydantic_settings:: canaille.core.configuration.SMPPSettings
.. autopydantic_settings:: canaille.core.configuration.ACLSettings
.. autoclass:: canaille.core.configuration.Permission
   :members:

.. autopydantic_settings:: canaille.oidc.configuration.OIDCSettings
.. autopydantic_settings:: canaille.oidc.configuration.JWTSettings
.. autopydantic_settings:: canaille.oidc.configuration.JWTMappingSettings

.. autopydantic_settings:: canaille.scim.configuration.SCIMSettings

.. autopydantic_settings:: canaille.backends.sql.configuration.SQLSettings
.. autopydantic_settings:: canaille.backends.ldap.configuration.LDAPSettings

Example file
============

Here is a configuration file example:

.. literalinclude :: ../../canaille/config.sample.toml
   :language: toml
   :caption: config.toml
