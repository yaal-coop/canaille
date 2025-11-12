.. _install_nix:

Linux packages
##############

At the moment, only `NixOS`_ provides a Canaille package.
For other distros, you must use a different way to install Canaille.

.. code-block:: console
   :substitutions:

   $ nix run "nixpkgs#canaille" run

.. warning::

   The current version of Canaille shipped by NixOS is 0.0.74,
   everything might not work as expected with this version.

.. _NixOS: https://mynixos.com/nixpkgs/package/canaille

Install
=======

The :ref:`install command <cli_install>` will apply most of the things needed to get Canaille working.
Depending on the configured :doc:`database <../databases>` it will create the SQL tables, or install the LDAP schemas for instance.

.. code-block:: console

    $ nix run "nixpkgs#canaille" install

Check
=====

After installation, you can test the network parameters in your configuration file using the :ref:`config check command <cli_config>`.
It will attempt to connect your :class:`SMTP server <canaille.core.configuration.SMTPSettings>`, or your :class:`SMPP server <canaille.core.configuration.SMPPSettings>` if defined.

.. code-block:: console

    $ nix run "nixpkgs#canaille" config check

Create the first user
======================

Once canaille is installed, soon enough you will need to add users.
To create your first user you can use the :ref:`canaille create <cli_create>` CLI.

.. code-block:: console

   $ nix run "nixpkgs#canaille" create user \
       --user-name admin \
       --password admin \
       --emails admin@mydomain.example \
       --given-name George \
       --family-name Abitbol \
       --formatted-name "George Abitbol"
