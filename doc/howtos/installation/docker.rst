.. _install_docker:

Docker
######

A Docker image is available on `DockerHub`_.
You can run Canaille simply by running the following command:

.. code-block:: console
   :substitutions:
   :caption: Run Canaille with the default configuration

   $ docker run --name canaille-web -p 8000:8000 yaalcoop/canaille:|version|

Canaille is published on the port 8000.
It might not be very usable as is though, as it is currently unconfigured, and thus running with a file-based database, without a production ready application server.

Generate a default configuration file with the following command:

.. code-block:: console
   :substitutions:
   :caption: Create a default configuration file for Canaille

   $ docker run --rm yaalcoop/canaille:|version| canaille config dump > canaille.toml

Then edit it as you like. You can find details on the configuration parameters on the :doc:`dedicated section <../../references/configuration>`. Then load the configuration with the following command:

.. code-block:: console
   :substitutions:
   :caption: Run Canaille with a configuration file

   $ docker run --name canaille-web -p 8000:8000 -v ./canaille.toml:/etc/canaille/config.toml yaalcoop/canaille:|version|

**Worker**

If you plan to use a :doc:`worker <../worker>` for asynchronous tasks (emails, SMS, provisioning), you need to configure a broker like Redis in your ``canaille.toml`` and launch the worker:

.. code-block:: console
   :substitutions:
   :caption: Run the Canaille worker with Docker

   $ docker run --name canaille-worker -v ./canaille.toml:/etc/canaille/config.toml yaalcoop/canaille:|version| worker

Docker Compose
==============

Here is an example of how to embed Canaille in Docker Compose with a worker and Redis:

.. code-block:: yaml
   :caption: `docker-compose.yml` example with worker

   services:
       redis:
           image: redis:alpine
           restart: unless-stopped

       canaille:
           hostname: canaille.localhost
           image: yaalcoop/canaille:latest
           ports:
           - 8000:8000
           volumes:
           - ./canaille.toml:/etc/canaille/config.toml:ro
           environment:
           - CANAILLE_CONFIG=/etc/canaille/config.toml
           - CANAILLE_BROKER_URL=redis://redis:6379
           depends_on:
           - redis

       worker:
           image: yaalcoop/canaille:latest
           command: worker
           volumes:
           - ./canaille.toml:/etc/canaille/config.toml:ro
           environment:
           - CANAILLE_CONFIG=/etc/canaille/config.toml
           - CANAILLE_BROKER_URL=redis://redis:6379
           depends_on:
           - redis

Run the containers:

.. code-block:: console
    :caption: Start canaille

    $ docker compose up

.. _DockerHub: https://hub.docker.com/r/yaalcoop/canaille

Install
=======

The :ref:`install command <cli_install>` will apply most of the things needed to get Canaille working.
Depending on the configured :doc:`database <../databases>` it will create the SQL tables, or install the LDAP schemas for instance.

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`devicon:docker` Docker
      :sync: docker

      .. code-block:: console
         :substitutions:

         $ docker run --rm -v ./canaille.toml:/etc/canaille/config.toml yaalcoop/canaille:|version| canaille install

   .. tab-item:: :iconify:`simple-icons:docker` Docker Compose
      :sync: docker-compose

      .. code-block:: console

         $ docker compose run --rm canaille canaille install

Check
=====

After installation, you can test the network parameters in your configuration file using the :ref:`config check command <cli_config>`.
It will attempt to connect your :class:`SMTP server <canaille.core.configuration.SMTPSettings>`, or your :class:`SMPP server <canaille.core.configuration.SMPPSettings>` if defined.

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`devicon:docker` Docker
      :sync: docker

      .. code-block:: console
         :substitutions:

         $ docker run --rm -v ./canaille.toml:/etc/canaille/config.toml yaalcoop/canaille:|version| canaille config check

   .. tab-item:: :iconify:`simple-icons:docker` Docker Compose
      :sync: docker-compose

      .. code-block:: console

         $ docker compose run --rm canaille canaille config check

Create the first user
======================

Once canaille is installed, soon enough you will need to add users.
To create your first user you can use the :ref:`canaille create <cli_create>` CLI.

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`devicon:docker` Docker
      :sync: docker

      .. code-block:: console
         :substitutions:

         $ docker run --rm -v ./canaille.toml:/etc/canaille/config.toml yaalcoop/canaille:|version| canaille create user \
             --user-name admin \
             --password admin \
             --emails admin@mydomain.example \
             --given-name George \
             --family-name Abitbol \
             --formatted-name "George Abitbol"

   .. tab-item:: :iconify:`simple-icons:docker` Docker Compose
      :sync: docker-compose

      .. code-block:: console

         $ docker compose run --rm canaille canaille create user \
             --user-name admin \
             --password admin \
             --emails admin@mydomain.example \
             --given-name George \
             --family-name Abitbol \
             --formatted-name "George Abitbol"
