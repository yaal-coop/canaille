Command Line Interface
======================

Canaille provide several commands to help administrator manage their data.

The configuration file has to be prefixed before running `canaille`. For readability's sake, it's omitted in the examples.

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
