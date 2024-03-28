Contributions
=============

Contributions are welcome!

The repository is hosted at `gitlab.com/yaal/canaille <https://gitlab.com/yaal/canaille>`_.

Discuss
-------

If you want to implement a feature or a bugfix, please start by discussing it with us on
the `bugtracker <https://gitlab.com/yaal/canaille/-/issues>`_ or the `matrix room
<https://matrix.to/#/#canaille-discuss:yaal.coop>`_.

Development environment
-----------------------

You can either run the demo locally or with docker.
After having launched the demo you have access to several services:

- A canaille server at `localhost:5000 <http://localhost:5000>`_
- A dummy client at `localhost:5001 <http://localhost:5001>`_
- Another dummy client at `localhost:5002 <http://localhost:5002>`_

The canaille server has some default users:

- A regular user which login and password are **user**;
- A moderator user which login and password are **moderator**;
- An admin user which admin and password are **admin**;
- A new user which login is **james**. This user has no password yet,
  and his first attempt to log-in would result in sending a password initialization
  email (if a smtp server is configurated).

Backends
~~~~~~~~

Canaille comes with several backends:

- a lightweight test purpose `memory` backend
- a `sql` backend, based on sqlalchemy
- a production-ready `LDAP` backend

Docker environment
~~~~~~~~~~~~~~~~~~

If you want to develop with docker, your browser needs to be able to reach the `canaille` container.
The docker-compose file exposes the right ports, but front requests are from outside the docker network:
the `canaille` url that makes sense for docker, points nowhere from your browser.
As exposed ports are on `localhost`, you need to tell your computer that `canaille` url means `localhost`.

To do that, you can add the following line to your `/etc/hosts`:

.. code-block:: console

    127.0.0.1   canaille

To launch containers, use:

.. code-block:: console

    cd demo
    # To run the demo with the sql backend:
    docker compose up

    # To run the demo with the memory backend:
    docker compose --file docker-compose-memory.yml up

    # To run the demo with the LDAP backend:
    docker compose --file docker-compose-ldap.yml up

Local environment
~~~~~~~~~~~~~~~~~

.. code-block:: console

    # To run the demo with the sql backend:
    ./demo/run.sh

    # To run the demo with the memory backend:
    ./demo/run.sh --backend memory

    # To run the demo with the LDAP backend:
    ./demo/run.sh --backend ldap

.. note ::
    If you want to run the demo locally with the LDAP backend, you need to have
    OpenLDAP installed on your system.

.. warning ::
    On Debian or Ubuntu systems, the OpenLDAP `slapd` binary usage might be restricted by apparmor,
    and thus makes the tests and the demo fail. This can be mitigated by removing apparmor restrictions
    on `slapd`.

    .. code-block:: console

        sudo apt install --yes apparmor-utils
        sudo aa-complain /usr/sbin/slapd

Populate the database
~~~~~~~~~~~~~~~~~~~~~

The demo database comes populated with some random users and groups. If you need more, you can generate
users and groups with the ``populate`` command:

.. code-block:: console

    # If using docker:
    docker compose exec canaille env CONFIG=conf-docker/canaille-ldap.toml poetry run canaille populate --nb 100 users  # or docker-compose

    # If running in local environment
    env CONFIG=conf/canaille-ldap.toml poetry run canaille populate  --nb 100 users

Adapt to use either the `ldap` or the `sql` configuration file. Note that this will not work with the memory backend.

Unit tests
----------

To run the tests, you just can run `poetry run pytest` and/or `tox` to test all the supported python environments.
Everything must be green before patches get merged.

To test a specific backend you can pass ``--backend memory``, ``--backend sql`` or ``--backend ldap`` to pytest and tox.

The test coverage is 100%, patches won't be accepted if not entirely covered. You can check the
test coverage with ``poetry run pytest --cov --cov-report=html`` or ``tox -e coverage -- --cov-report=html``.
You can check the HTML coverage report in the newly created `htmlcov` directory.

Code style
----------

We use `ruff <https://docs.astral.sh/ruff/>`_ along with other tools to format our code.
Please run ``tox -e style`` on your patches before submiting them.
In order to perform a style check and correction at each commit you can use our
`pre-commit <https://pre-commit.com/>`_ configuration with ``pre-commit install``.

Front
-----

The interface is built upon the `Fomantic UI <https://fomantic-ui.com/>`_ CSS framework.
The dynamical parts of the interface use `htmx <https://htmx.org/>`_.

- Using Javascript in the interface is tolerated, but the whole website MUST be accessible
  for browsers without Javascript support, and without any feature loss.
- Because of Fomantic UI we have a dependency to jQuery, however new contributions should
  not depend on jQuery at all.
  See the `related issue <https://gitlab.com/yaal/canaille/-/issues/130>`_.

Translations
------------

.. include:: ../canaille/translations/README.md
   :parser: myst_parser.sphinx_

Documentation
-------------

The documentation is generated when the tests run:

.. code-block:: console

    tox -e doc

The generated documentation is located at `./build/sphinx/html`.
