.. _install_docker:

Docker & Podman
###############

A Docker image is available on `DockerHub`_.
You can run Canaille simply by running the following command:

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`devicon:docker` Docker
      :sync: docker

      .. code-block:: console
         :substitutions:
         :caption: Run Canaille with the default configuration

         $ docker run --name canaille-web -p 8000:8000 yaalcoop/canaille:|version|

   .. tab-item:: :iconify:`devicon:podman` Podman
      :sync: podman

      .. code-block:: console
         :substitutions:
         :caption: Run Canaille with the default configuration

         $ podman run --name canaille-web -p 8000:8000 yaalcoop/canaille:|version|

Canaille is published on the port 8000.
It might not be very usable as is though, as it is currently unconfigured, and thus running with a file-based database, without a production ready application server.

Generate a default configuration file with the following command:

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`devicon:docker` Docker
      :sync: docker

      .. code-block:: console
         :substitutions:
         :caption: Create a default configuration file for Canaille

         $ mkdir -p data
         $ docker run --rm yaalcoop/canaille:|version| config dump > data/canaille.toml

   .. tab-item:: :iconify:`devicon:podman` Podman
      :sync: podman

      .. code-block:: console
         :substitutions:
         :caption: Create a default configuration file for Canaille

         $ mkdir -p data
         $ podman run --rm yaalcoop/canaille:|version| config dump > data/canaille.toml

Then edit it as you like. You can find details on the configuration parameters on the :doc:`dedicated section <../../references/configuration>`.
Then load the configuration with the following command:

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`devicon:docker` Docker
      :sync: docker

      .. code-block:: console
         :substitutions:
         :caption: Run Canaille with a configuration file

         $ docker run --name canaille-web -p 8000:8000 -v ./data:/data yaalcoop/canaille:|version|

   .. tab-item:: :iconify:`devicon:podman` Podman
      :sync: podman

      .. code-block:: console
         :substitutions:
         :caption: Run Canaille with a configuration file

         $ podman run --name canaille-web -p 8000:8000 -v ./data:/data yaalcoop/canaille:|version|


**Worker**

If you plan to use a :doc:`worker <../worker>` for asynchronous tasks (emails, SMS, provisioning), you need to configure a broker like Redis in your ``canaille.toml`` and launch the worker:

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`devicon:docker` Docker
      :sync: docker

      .. code-block:: console
         :substitutions:
         :caption: Run the Canaille worker

         $ docker run --name canaille-worker -v ./data:/data yaalcoop/canaille:|version| worker

   .. tab-item:: :iconify:`devicon:podman` Podman
      :sync: podman

      .. code-block:: console
         :substitutions:
         :caption: Run the Canaille worker

         $ podman run --name canaille-worker -v ./data:/data yaalcoop/canaille:|version| worker

Docker Compose & Podman Compose
===============================

Here is an example of how to embed Canaille in Docker Compose or Podman Compose with a worker and Redis:

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
           - ./data:/data
           environment:
           - CANAILLE_BROKER_URL=redis://redis:6379
           depends_on:
           - redis

       worker:
           image: yaalcoop/canaille:latest
           command: worker
           volumes:
           - ./data:/data
           environment:
           - CANAILLE_BROKER_URL=redis://redis:6379
           depends_on:
           - redis

Run the containers:

.. tab-set::
   :class: outline

   .. tab-item:: :iconify:`simple-icons:docker` Docker Compose
      :sync: docker-compose

      .. code-block:: console
          :caption: Start canaille

          $ docker compose up

   .. tab-item:: :iconify:`devicon:podman` Podman Compose
      :sync: podman-compose

      .. code-block:: console
          :caption: Start canaille

          $ podman compose up

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

         $ docker run --rm -v ./data:/data yaalcoop/canaille:|version| install

   .. tab-item:: :iconify:`devicon:podman` Podman
      :sync: podman

      .. code-block:: console
         :substitutions:

         $ podman run --rm -v ./data:/data yaalcoop/canaille:|version| install

   .. tab-item:: :iconify:`simple-icons:docker` Docker Compose
      :sync: docker-compose

      .. code-block:: console

         $ docker compose run --rm canaille install

   .. tab-item:: :iconify:`devicon:podman` Podman Compose
      :sync: podman-compose

      .. code-block:: console

         $ podman compose run --rm canaille install

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

         $ docker run --rm -v ./data:/data yaalcoop/canaille:|version| config check

   .. tab-item:: :iconify:`devicon:podman` Podman
      :sync: podman

      .. code-block:: console
         :substitutions:

         $ podman run --rm -v ./data:/data yaalcoop/canaille:|version| config check

   .. tab-item:: :iconify:`simple-icons:docker` Docker Compose
      :sync: docker-compose

      .. code-block:: console

         $ docker compose run --rm canaille config check

   .. tab-item:: :iconify:`devicon:podman` Podman Compose
      :sync: podman-compose

      .. code-block:: console

         $ podman compose run --rm canaille config check

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

         $ docker run --rm -v ./data:/data yaalcoop/canaille:|version| create user \
             --user-name admin \
             --password admin \
             --emails admin@mydomain.example \
             --given-name George \
             --family-name Abitbol \
             --formatted-name "George Abitbol"

   .. tab-item:: :iconify:`devicon:podman` Podman
      :sync: podman

      .. code-block:: console
         :substitutions:

         $ podman run --rm -v ./data:/data yaalcoop/canaille:|version| create user \
             --user-name admin \
             --password admin \
             --emails admin@mydomain.example \
             --given-name George \
             --family-name Abitbol \
             --formatted-name "George Abitbol"

   .. tab-item:: :iconify:`simple-icons:docker` Docker Compose
      :sync: docker-compose

      .. code-block:: console

         $ docker compose run --rm canaille create user \
             --user-name admin \
             --password admin \
             --emails admin@mydomain.example \
             --given-name George \
             --family-name Abitbol \
             --formatted-name "George Abitbol"

   .. tab-item:: :iconify:`devicon:podman` Podman Compose
      :sync: podman-compose

      .. code-block:: console

         $ podman compose run --rm canaille create user \
             --user-name admin \
             --password admin \
             --emails admin@mydomain.example \
             --given-name George \
             --family-name Abitbol \
             --formatted-name "George Abitbol"
