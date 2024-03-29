Configuration
#############

Canaille can be configured either by a environment variables, or by a `toml` configuration file which path is passed in the ``CONFIG`` environment variable.

Toml file
=========

::

    SECRET_KEY = "very-secret"

    [CANAILLE]
    NAME = "My organization"

    [CANAILLE_SQL]
    DATABASE_URI = "postgresql://user:password@localhost/database"
    ...

You can have a look at the :ref:`configuration:Example file` for inspiration.

Environment variables
=====================

In addition, parameters that have not been set in the configuration file can be read from environment variables.
The way environment variables are parsed can be read from the `pydantic-settings documentation <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#parsing-environment-variable-values>`_.

Settings will also be read from a local ``.env`` file if present.

.. TODO: Uncomment this when pydantic-settings implements nested secrets directories
   https://github.com/pydantic/pydantic-settings/issues/154

    Secret parameters
    =================

    A ``SECRETS_DIR`` environment variable can be passed as an environment variable, being a path to a directory in which are stored files named after the configuration settings.

    For instance, you can set ``SECRETS_DIR=/run/secrets`` and put your secret key in the file ``/run/secrets/SECRET_KEY``.

Parameters
==========

.. autopydantic_settings:: canaille.app.configuration.RootSettings

.. autopydantic_settings:: canaille.core.configuration.CoreSettings
.. autopydantic_settings:: canaille.core.configuration.SMTPSettings
.. autopydantic_settings:: canaille.core.configuration.ACLSettings
.. auto_autoenum:: canaille.core.configuration.Permission

.. autopydantic_settings:: canaille.oidc.configuration.OIDCSettings

.. autopydantic_settings:: canaille.oidc.configuration.JWTSettings
.. autopydantic_settings:: canaille.oidc.configuration.JWTMappingSettings

.. autopydantic_settings:: canaille.backends.sql.configuration.SQLSettings
.. autopydantic_settings:: canaille.backends.ldap.configuration.LDAPSettings

Example file
============

Here is a configuration file example:

.. literalinclude :: ../canaille/config.sample.toml
   :language: toml
