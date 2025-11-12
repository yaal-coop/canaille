.. _install_binaries:

Binary
######

Canaille provides a ready-to-use single file executable for Linux.
The binary installation is the easiest way to get a production-ready Canaille release, though this is not the most customizable.
This is generally the recommended method to use Canaille in production.

.. code-block:: console
   :substitutions:

   $ wget https://github.com/yaal-coop/canaille/releases/download/|version|/canaille -o canaille
   $ chmod +x canaille

.. note::

    Canaille binaries comes with lesser performances than other installation methods on startup.
    This is generally not an issue, since Canaille is used as a long-running service,
    but if this is important for you, you might want to choose another installation method.

Then you can run the Canaille web service with:

.. code-block:: console
   :substitutions:

   $ ./canaille run

Install
=======

The :ref:`install command <cli_install>` will apply most of the things needed to get Canaille working.
Depending on the configured :doc:`database <../databases>` it will create the SQL tables, or install the LDAP schemas for instance.

.. code-block:: console

    $ ./canaille install

Check
=====

After installation, you can test the network parameters in your configuration file using the :ref:`config check command <cli_config>`.
It will attempt to connect your :class:`SMTP server <canaille.core.configuration.SMTPSettings>`, or your :class:`SMPP server <canaille.core.configuration.SMPPSettings>` if defined.

.. code-block:: console

    $ ./canaille config check

Create the first user
======================

Once canaille is installed, soon enough you will need to add users.
To create your first user you can use the :ref:`canaille create <cli_create>` CLI.

.. code-block:: console

   $ ./canaille create user \
       --user-name admin \
       --password admin \
       --emails admin@mydomain.example \
       --given-name George \
       --family-name Abitbol \
       --formatted-name "George Abitbol"
