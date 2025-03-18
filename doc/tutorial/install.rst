Installation
############

This page describes how to get and set-up Canaille.

*I have no time, spare me the details !*

.. parsed-literal::

   wget https://github.com/yaal-coop/canaille/releases/download/\ |version|\ /canaille -o canaille
   chmod +x canaille
   export CONFIG=/path/to/my/config.toml
   canaille config dump
   $EDITOR $CONFIG
   canaille install
   canaille config check
   canaille create user --user-name admin --password admin --emails admin@mydomain.example --given-name George --family-name Abitbol

Get the code
============

Docker image
------------

A Docker image is available on `dockerhub`_.

.. code-block:: console

    docker pull yaalcoop/canaille:latest
    docker run -it -p 5000:5000 yaalcoop/canaille:latest


.. _dockerhub: https://hub.docker.com/r/yaalcoop/canaille

Binaries
--------

Canaille provides a ready-to-use single file executable for Linux.
The binary installation is the easiest way to get a production-ready Canaille release, though this is not the most customizable.
This is generally the recommended method to use Canaille in production.

.. parsed-literal::

    wget https://github.com/yaal-coop/canaille/releases/download/\ |version|\ /canaille -o canaille
    chmod +x canaille

.. note::

    Canaille binaries comes with lesser performances than other installation methods on startup.
    This is generally not an issue, since Canaille is used as a long-running service,
    but if this is important for you, you might want to choose another installation method.

Linux packages
--------------

At the moment, only `NixOS`_ provides a Canaille package.
For other distros, you must use a different way to install Canaille.

.. _NixOS: https://mynixos.com/nixpkgs/package/canaille

Python package
--------------

Canaille provides a `Python package <Canaille_PyPI>`_ that you can install with package managers like ``uv`` or ``pip``.
This is the recommended method if you want fast CLI performances, if you need to customize the dependencies, or if you want to use Canaille in a development environment.

In the following example, we use a custom virtualenv to install Canaille.
Note that you should customize the ``EXTRAS`` packages, depending on your needs.

.. code-block:: bash
   :caption: Canaille installation using a Python virtualenv

   sudo mkdir --parents /opt/canaille
   virtualenv /opt/canaille/env
   . /opt/canaille/env/bin/activate
   pip install "canaille[EXTRAS]"
   canaille --version

.. _Canaille_PyPI: https://pypi.org/project/Canaille

.. note::

   In the rest of the documentation, we consider that your virtualenv is activated,
   and that the ``canaille`` command is available.

Extras
~~~~~~

Canaille provides different package options:

- `front` provides all the things needed to produce the user interface;
- `oidc` provides the dependencies to perform OAuth2/OIDC authentication;
- `ldap` provides the dependencies to enable the LDAP backend;
- `sqlite` provides the dependencies to enable the SQLite backend;
- `postgresql` provides the dependencies to enable the PostgreSQL backend;
- `mysql` provides the dependencies to enable the MySQL backend;
- `sentry` provides sentry integration to watch Canaille exceptions;
- `otp` provides the dependencies to enable one-time password authentication;
- `sms` provides the dependencies to enable sms sending;
- `server` provides the dependencies to run a production server.

They can be installed with:

.. code-block:: bash

   pip install "canaille[front,oidc,postgresql,server]"

Configure
=========

The :doc:`configuration documentation<../references/configuration>` describe several ways to configure Canaille,
however the most common is to use a TOML configuration file and pass its path with the :envvar:`CONFIG` environment variable.
A configuration file with default values can be initialized with the :ref:`config dump <cli_config>` command.

.. code-block:: bash
    :caption: Initialize a configuration file.

    export CONFIG=/path/to/my/config.toml
    canaille config dump

You can then edit your configuration file and tune its values.
Have a look at the :ref:`reference <references/configuration:Parameters>` to know the exhaustive list of available parameters.

.. note::

   In the rest of the documentation, we consider that your Canaille instance is configured by one of the available methods (either with a :envvar:`CONFIG` environment var, either with ``.env`` files etc.).

Install
=======

The :ref:`install command <cli_install>` will apply most of the things needed to get Canaille working.
Depending on the configured :doc:`database <databases>` it will create the SQL tables, or install the LDAP schemas for instance.

.. code-block:: bash

    canaille install

Check
=====

After a manual installation, you can test the network parameters in your configuration file using the :ref:`config check command <cli_config>`.
It will attempt to connect your :class:`SMTP server <canaille.core.configuration.SMTPSettings>`, or your :class:`SMPP server <canaille.core.configuration.SMPPSettings>` if defined.

.. code-block:: bash

    canaille config check

Create the first user
=====================

Once canaille is installed, soon enough you will need to add users.
To create your first user you can use the :ref:`canaille create <cli_create>` CLI.

.. code-block:: bash

   canaille create user \
       --user-name admin \
       --password admin \
       --emails admin@mydomain.example \
       --given-name George \
       --family-name Abitbol
