Getting started
###############

This tutorial will guide you through your first steps with Canaille, from installation to testing your first OAuth authentication flow.

By the end of this tutorial, you will have:

- Ran Canaille on your system
- Created your first users and groups
- Tested a complete authentication flow

Step 1: Install Canaille
=========================

Download the latest Canaille binary with your preferred method: :ref:`one-file binary <install_binaries>`, :ref:`Docker <install_docker>`, or :ref:`uv or pip <install_python>`.

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`mdi:file-download` Binary
      :sync: binary

      .. code-block:: console
         :substitutions:

         $ wget https://github.com/yaal-coop/canaille/releases/download/|version|/canaille -O canaille
         $ chmod +x canaille

   .. tab-item:: :iconify:`devicon:docker` Docker
      :sync: docker

      .. code-block:: console

         $ docker pull yaalcoop/canaille:latest

   .. tab-item:: :iconify:`material-icon-theme:uv` uv
      :sync: uv

      .. code-block:: console

         $ uvx "canaille[front,oidc,server]" --version

   .. tab-item:: :iconify:`devicon:pypi` pip
      :sync: pip

      .. code-block:: console

         $ pip install "canaille[front,oidc,server]"

.. note::

    For uv and pip, the ``[front,oidc,server]`` extras install basic dependencies for running Canaille with its web interface, OpenID Connect support, and built-in server.
    For more information about available extras, see :ref:`package_extras`.

Check the Canaille version:

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`mdi:file-download` Binary
      :sync: binary

      .. code-block:: console

         $ ./canaille --version

   .. tab-item:: :iconify:`devicon:docker` Docker
      :sync: docker

      .. code-block:: console

         $ docker run --rm yaalcoop/canaille:latest --version

   .. tab-item:: :iconify:`material-icon-theme:uv` uv
      :sync: uv

      .. code-block:: console

         $ uvx "canaille[front,oidc,server]" --version

   .. tab-item:: :iconify:`devicon:pypi` pip
      :sync: pip

      .. code-block:: console

         $ canaille --version

Step 2: Create Your Configuration File
=======================================

While you can run Canaille with zero configuration, to use Canaille in production you will
need to tune some settings.
Let's create a configuration file with default values:

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`mdi:file-download` Binary
      :sync: binary

      .. code-block:: console

         $ export CANAILLE_CONFIG=canaille.toml
         $ ./canaille config dump --path $CANAILLE_CONFIG

   .. tab-item:: :iconify:`devicon:docker` Docker
      :sync: docker

      .. code-block:: console

         $ docker run --rm yaalcoop/canaille:latest config dump > canaille.toml

   .. tab-item:: :iconify:`material-icon-theme:uv` uv
      :sync: uv

      .. code-block:: console

         $ export CANAILLE_CONFIG=canaille.toml
         $ uvx "canaille[front,oidc,server]" config --path $CANAILLE_CONFIG

   .. tab-item:: :iconify:`devicon:pypi` pip
      :sync: pip

      .. code-block:: console

         $ export CANAILLE_CONFIG=canaille.toml
         $ canaille config dump --path $CANAILLE_CONFIG

This creates a ``canaille.toml`` file in your current directory with sensible defaults.

Open the file in your text editor and make a few essential changes,
basically choosing a :attr:`~canaille.app.configuration.RootSettings.SECRET_KEY`
and a :attr:`~canaille.core.configuration.CoreSettings.NAME` for your instance.

.. code-block:: toml
   :caption: canaille.toml

   SECRET_KEY = "change-me-to-a-random-string"

   [CANAILLE]
   NAME = "My Canaille Tutorial"

.. tip::

   Change the ``SECRET_KEY`` to a random string. You can generate one with:

   .. code-block:: console

      $ python3 -c "import secrets; print(secrets.token_hex(32))"

You can have a look at the :doc:`configuration reference <../references/configuration>` to
get the exhaustive list of configuration parameters.

Step 3: Set up the database
===========================

By default Canaille use a SQLite database named ``canaille.sqlite`` in the current directory,
but you might want to use another database, say PostgreSQL, in which case you will need to
create the database first and then edit your configuration file.

Create PostgreSQL database
---------------------------

If you choose to use PostgreSQL, you need to create a database, say ``canaille``,
and a user with appropriate permissions:

.. code-block:: console

   $ sudo -u postgres createuser --pwprompt canaille
   $ sudo -u postgres createdb --owner=canaille_user canaille

Then update your configuration file:

.. code-block:: toml
   :caption: canaille.toml

   [CANAILLE_SQL]
   DATABASE_URI = "postgresql://canaille:your_secure_password@localhost/canaille"

Initialize the database
-----------------------

Then let Canaille create the tables and run the migrations:

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`mdi:file-download` Binary
      :sync: binary

      .. code-block:: console

         $ ./canaille install

   .. tab-item:: :iconify:`devicon:docker` Docker
      :sync: docker

      .. code-block:: console

         $ docker run --rm -v ./canaille.toml:/etc/canaille/config.toml yaalcoop/canaille:latest install

   .. tab-item:: :iconify:`material-icon-theme:uv` uv
      :sync: uv

      .. code-block:: console

         $ uvx "canaille[front,oidc,server]" install

   .. tab-item:: :iconify:`devicon:pypi` pip
      :sync: pip

      .. code-block:: console

         $ canaille install

To read in more depth how to configure SQL databases and LDAP directories,
have a look at :doc:`../howtos/databases`.

Step 4: Create Your First Admin User
=====================================

Before running the web interface you need to create a first user.
By default, if you did not configure :attr:`~canaille.core.configuration.CoreSettings.ACL`,
an user called ``admin`` gets all the privileges.

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`mdi:file-download` Binary
      :sync: binary

      .. code-block:: console

         $ ./canaille create user \
             --user-name admin \
             --password admin123 \
             --emails admin@example.com \
             --given-name Admin \
             --family-name User \
             --formatted-name "Admin User"

   .. tab-item:: :iconify:`devicon:docker` Docker
      :sync: docker

      .. code-block:: console

         $ docker run --rm -v ./canaille.toml:/etc/canaille/config.toml \
             yaalcoop/canaille:latest create user \
             --user-name admin \
             --password admin123 \
             --emails admin@example.com \
             --given-name Admin \
             --family-name User \
             --formatted-name "Admin User"

   .. tab-item:: :iconify:`material-icon-theme:uv` uv
      :sync: uv

      .. code-block:: console

         $ uvx "canaille[front,oidc,server]" create user \
             --user-name admin \
             --password admin123 \
             --emails admin@example.com \
             --given-name Admin \
             --family-name User \
             --formatted-name "Admin User"

   .. tab-item:: :iconify:`devicon:pypi` pip
      :sync: pip

      .. code-block:: console

         $ canaille create user \
             --user-name admin \
             --password admin123 \
             --emails admin@example.com \
             --given-name Admin \
             --family-name User \
             --formatted-name "Admin User"

.. warning::

   For this tutorial, we use a simple password. In production, always use strong, unique passwords!

Step 5: Start Canaille
=======================

Now we are ready to start the Canaille server:

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`mdi:file-download` Binary
      :sync: binary

      .. code-block:: console

         $ ./canaille run

   .. tab-item:: :iconify:`devicon:docker` Docker
      :sync: docker

      .. code-block:: console

         $ docker run --rm -p 8000:8000 \
             -v ./canaille.toml:/etc/canaille/config.toml \
             yaalcoop/canaille:latest

   .. tab-item:: :iconify:`material-icon-theme:uv` uv
      :sync: uv

      .. code-block:: console

         $ uvx "canaille[front,oidc,server]" run

   .. tab-item:: :iconify:`devicon:pypi` pip
      :sync: pip

      .. code-block:: console

         $ canaille run

You should see output similar to:

.. code-block:: console

   [2025-01-15 10:00:00 +0100] [12345] [INFO] Running on http://0.0.0.0:8000 (CTRL + C to quit)

Canaille is now running! Keep the terminal open.

Step 6: Access the Web Interface
=================================

.. screenshot:: |canaille|/login
   :align: right
   :width: 275px

   The login page.

Open your web browser and navigate to:

.. code-block:: text

   http://localhost:8000

You should see the Canaille landing page. Click on **Sign in** in the bottom right corner.

.. screenshot:: |canaille|/profile/admin
   :context: admin
   :align: right
   :width: 275px

   Your profile page after logging in.

Log in with the credentials you created:

- **User name**: admin
- **Password**: admin123

After logging in, you'll see your profile page. Take a moment to explore the interface.

Step 7: Create a Regular User
==============================

.. screenshot:: |canaille|/profile
   :context: admin
   :align: right
   :width: 275px

   The user creation form.

Now let's create a regular user account. From the web interface:

1. Click on **Users** in the navigation menu
2. Click the **+ Add** button
3. Fill in the form:

   - **User name**: john
   - **Family name**: Doe
   - **Given name**: John
   - **Formatted name**: John Doe
   - **Email**: john@example.com
   - **Password**: user123

4. Click **Save**

You've just created your first regular user!

Step 8: Create a Group
=======================

.. screenshot:: |canaille|/groups/add
   :context: admin
   :align: right
   :width: 275px

   The group creation form.

Groups help organize users. Let's create one:

1. Click on **Groups** in the navigation menu
2. Click the **+ Add** button
3. Fill in:

   - **Name**: developers
   - **Description**: Development team

4. In the **Members** section, select both **admin** and **john**
5. Click **Save**

Great! You now have users organized in a group.
