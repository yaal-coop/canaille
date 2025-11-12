.. _install_python:

Python package
##############

Canaille provides a `Python package <Canaille_PyPI>`_ that you can install with package managers like ``uv`` or ``pip``.
This is the recommended method if you want fast CLI performances, if you need to customize the dependencies, or if you want to use Canaille in a development environment.

In the following example, we use a custom virtualenv to install Canaille.
Note that you should customize the ``EXTRAS`` packages, depending on your needs.

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`material-icon-theme:uv` uv
      :sync: uv

      .. code-block:: console

         $ uvx "canaille[EXTRAS]" run

   .. tab-item:: :iconify:`devicon:pypi` pip
      :sync: pip

      .. code-block:: console

         $ virtualenv env
         $ env/bin/pip install "canaille[EXTRAS]"
         $ env/bin/canaille run

.. _Canaille_PyPI: https://pypi.org/project/Canaille

.. _package_extras:

Extras
======

Canaille provides different package options:

- `front` provides all the things needed to produce the user interface;
- `oidc` provides the dependencies to perform OAuth2/OIDC authentication;
- `ldap` provides the dependencies to enable the LDAP backend;
- `sqlite` provides the dependencies to enable the SQLite backend;
- `postgresql` provides the dependencies to enable the PostgreSQL backend;
- `mysql` provides the dependencies to enable the MySQL backend;
- `sentry` provides sentry integration to watch Canaille exceptions;
- `otp` provides the dependencies to enable one-time passcode authentication;
- `sms` provides the dependencies to enable sms sending;
- `server` provides the dependencies to run a production server.

They can be installed with:

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`material-icon-theme:uv` uv
      :sync: uv

      .. code-block:: console

         $ uvx "canaille[front,oidc,postgresql,server]" run

   .. tab-item:: :iconify:`devicon:pypi` pip
      :sync: pip

      .. code-block:: console

         $ virtualenv env
         $ env/bin/pip install "canaille[front,oidc,postgresql,server]"
         $ env/bin/canaille run

Install
=======

The :ref:`install command <cli_install>` will apply most of the things needed to get Canaille working.
Depending on the configured :doc:`database <../databases>` it will create the SQL tables, or install the LDAP schemas for instance.

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`material-icon-theme:uv` uv
      :sync: uv

      .. code-block:: console

         $ uvx "canaille[EXTRAS]" install

   .. tab-item:: :iconify:`devicon:pypi` pip
      :sync: pip

      .. code-block:: console

         $ canaille install

Check
=====

After installation, you can test the network parameters in your configuration file using the :ref:`config check command <cli_config>`.
It will attempt to connect your :class:`SMTP server <canaille.core.configuration.SMTPSettings>`, or your :class:`SMPP server <canaille.core.configuration.SMPPSettings>` if defined.

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`material-icon-theme:uv` uv
      :sync: uv

      .. code-block:: console

         $ uvx "canaille[EXTRAS]" config check

   .. tab-item:: :iconify:`devicon:pypi` pip
      :sync: pip

      .. code-block:: console

         $ canaille config check

Create the first user
======================

Once canaille is installed, soon enough you will need to add users.
To create your first user you can use the :ref:`canaille create <cli_create>` CLI.

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`material-icon-theme:uv` uv
      :sync: uv

      .. code-block:: console

         $ uvx "canaille[EXTRAS]" create user \
             --user-name admin \
             --password admin \
             --emails admin@mydomain.example \
             --given-name George \
             --family-name Abitbol \
             --formatted-name "George Abitbol"

   .. tab-item:: :iconify:`devicon:pypi` pip
      :sync: pip

      .. code-block:: console

         $ canaille create user \
             --user-name admin \
             --password admin \
             --emails admin@mydomain.example \
             --given-name George \
             --family-name Abitbol \
             --formatted-name "George Abitbol"
