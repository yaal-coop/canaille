Command Line Interface
======================

Canaille provide several commands to help administrator manage their data.

Generally, some configuration has to be loaded by `Canaille`.
This can be achieved by :ref:`configuration loading method<references/configuration:Load the configuration>` available, but most of the time a ``CONFIG`` environment variable is used.
For the sake of readability, it is omitted in the following examples.

.. code-block:: shell

    env CONFIG=path/to/config.toml canaille ...

.. _cli_check:

.. click:: canaille.app.commands:check
   :prog: canaille check
   :nested: full

.. _cli_clean:

.. click:: canaille.oidc.commands:clean
   :prog: canaille clean
   :nested: full

.. _cli_dump:

.. click:: canaille.backends.commands:dump
   :prog: canaille dump
   :nested: full

.. _cli_install:

.. click:: canaille.app.commands:install
   :prog: canaille install
   :nested: full

.. _cli_populate:

.. click:: canaille.core.commands:populate
   :prog: canaille populate
   :nested: full

.. _cli_get:

.. click:: doc.commands:get
   :prog: canaille get
   :nested: full

.. _cli_set:

.. click:: doc.commands:set
   :prog: canaille set
   :nested: full

.. _cli_create:

.. click:: doc.commands:create
   :prog: canaille create
   :nested: full

.. _cli_delete:

.. click:: doc.commands:delete
   :prog: canaille delete
   :nested: full

.. _cli_reset_otp:

.. click:: canaille.backends.commands:reset_otp
   :prog: canaille reset-otp
   :nested: full
