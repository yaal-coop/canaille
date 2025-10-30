Task worker
###########

Canaille can delegate long-running operations that involves network requests to a task worker.
This ensures the web interface responds quickly to user, this is especially pertinent if you use Canaille as a :doc:`../howtos/provisioning` client.
The tasks that are delegated to the worker are:

- Propagation of provisioning events among applications.
- Sending emails.
- Sending SMS.

Configuration
=============

To run a task worker you first need to fill the :attr:`~canaille.app.configuration.RootSettings.BROKER_URL` configuration parameter. When unset Canaille will perform long-running tasks synchronously, when set Canaille will communicate with the task worker through a messaging interface like `Redis <https://redis.io>`__ or `RabbitMQ <https://www.rabbitmq.com>`__.

The URL can have values like:

- ``redis://localhost:6379``
- ``amqp://localhost``
- ``redis://username:password@redis.example:6379/0``
- ``amqp://guest:guest@localhost:5672/?heartbeat=30&connection_timeout=10``

If you want to use other communication backends, like SQL, you need to also set the :attr:`~canaille.app.configuration.RootSettings.BROKER` parameter.

.. code-block:: toml
   :caption: Example of worker configuration for SQLite

    BROKER="dramatiq_sqlite:SQLBroker"
    BROKER_URL="sqlite://broker.sqlite"

Dependencies
============

Canaille natively supports Redis and RabbitMQ, their support is embedded in the Docker image and binary file.
If you installed Canaille through its Python package, you will probably want to install the ``redis`` or ``rabbitmq`` extras.
If you want to use other backends you will need to install the dependencies yourself. For instance to support SQLite you can install `dramatiq-sqlite <https://pypi.org/project/dramatiq-sqlite/>`__.

Service
=======

Now you need to run the worker service. This can be done with the :ref:`cli_worker` command:

.. code-block:: console
   :caption: Running the Canaille worker

   $ env CANAILLE_CONFIG=canaille.toml canaille worker
