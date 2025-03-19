Contribution
============

Contributions are welcome!

The repository is hosted at `gitlab.com/yaal/canaille <https://gitlab.com/yaal/canaille>`_.

Discuss
-------

If you want to implement a feature or a bugfix, please start by discussing it with us on
the `bugtracker <https://gitlab.com/yaal/canaille/-/issues>`_ or the `matrix room
<https://matrix.to/#/#canaille-discuss:yaal.coop>`_.

Development environment
-----------------------

You can either run the development server locally or with Docker.

After having launched the development server, you have access to several services:

- A canaille server at `canaille.localhost:5000 <http://canaille.localhost:5000>`__
- A dummy client at `client1.localhost:5001 <http://client1.localhost:5001>`__
- Another dummy client at `client2.localhost:5002 <http://client2.localhost:5002>`__
- A mail catcher at `maildump.localhost:1080 <http://maildump.localhost:1080>`__

The canaille server has some default users:

- A regular user which login and password are **user**;
- A moderator user which login and password are **moderator**;
- An admin user which admin and password are **admin**;
- A new user which login is **james**. This user has no password yet,
  and his first attempt to log-in would result in sending a password initialization
  email (if a smtp server is configured).

Backends
~~~~~~~~

Canaille comes with several backends:

- a lightweight test purpose `memory` backend
- a `sql` backend, based on sqlalchemy
- a production-ready `LDAP` backend

.. _local_environment:

Local environment
~~~~~~~~~~~~~~~~~

The only tool required for local development is `uv`.
Make sure to have uv `installed on your computer <https://docs.astral.sh/uv/getting-started/installation/>`_
to be able to hack Canaille.

Initialize your development environment with:

- ``uv sync --all-groups --all-extras`` if you want to have everything at your fingertips. Note that it may compile some Python dependencies that would expect things to be installed on your system;
- ``uv sync --extra front --extra oidc`` to have a minimal working development environment. This will allow you to run the tests with ``uv pytest --backend memory``.
- ``uv sync --extra front --extra oidc --extra sqlite`` to have a minimal working development environment with SQLite backend support. This will allow you to run the tests with ``uv pytest --backend sql``.
- ``uv sync --extra front --extra oidc --extra ldap`` to have a minimal working development environment with LDAP backend support. This will allow you to run the tests with ``uv pytest --backend ldap``.
  Some dependencies of Canaille might need to be compiled, so you probably want to check that `GCC` and `cargo` are available on your computer.

SQL
^^^
With the SQL backend, the development server will load and save data in a local sqlite database.

.. code-block:: console
    :caption: Run the development server with the SQL backend

    uv run devserver

Memory
^^^^^^
With the memory backend, all data is lost when Canaille stops.

.. code-block:: console
    :caption: Run the development server with the memory backend

    uv run devserver --backend memory

LDAP
^^^^
With the LDAP backend, all data is lost when Canaille stops.

.. code-block:: console
    :caption: Run the development server with the LDAP backend

    uv run devserver --backend ldap

.. note ::
    If you want to run the development server locally with the LDAP backend, you need to have
    `OpenLDAP <https://www.openldap.org/>`_ installed on your system.
    It is generally shipped under the ``slapd`` or ``openldap`` package name.

.. warning ::
    On Debian or Ubuntu systems, the OpenLDAP `slapd` binary usage might be restricted by apparmor,
    and thus makes the tests and the development server fail. This can be mitigated by removing apparmor restrictions
    on `slapd`.

    .. code-block:: console

        sudo apt install --yes apparmor-utils
        sudo aa-complain /usr/sbin/slapd

Docker environment
~~~~~~~~~~~~~~~~~~

SQL
^^^
With the SQL backend, the development server will load and save data in a local sqlite database.

.. code-block:: console
    :caption: Run the development server with the SQL backend

    cd dev
    docker compose up

Memory
^^^^^^
With the memory backend, all data is lost when Canaille stops.

.. code-block:: console
    :caption: Run the development server with the memory backend

    cd dev
    docker compose --file docker-compose-memory.yml up

LDAP
^^^^
With the LDAP backend, all data is lost when Canaille stops.

.. code-block:: console
    :caption: Run the development server with the LDAP backend

    cd dev
    docker compose --file docker-compose-ldap.yml up

Populate the database
~~~~~~~~~~~~~~~~~~~~~

The development server database comes populated with some random users and groups. If you need more, you can generate
users and groups with the ``populate`` command:

.. code-block:: console

    # If using docker:
    docker compose exec canaille env CANAILLE__DATABASE=<backend> CONFIG=conf/canaille.toml uv run canaille populate --nb 100 users  # or docker-compose

    # If running in local environment
    env CANAILLE__DATABASE=<backend> CONFIG=conf/canaille.toml uv run canaille populate  --nb 100 users

Adapt to use either the `ldap` or the `sql` configuration file. Note that this will not work with the memory backend.

Unit tests
----------

To run the tests, you just can run `uv run pytest` and/or `uv run tox` to test all the supported python environments.
Everything must be green before patches get merged.

To test a specific backend you can pass ``--backend memory``, ``--backend sql`` or ``--backend ldap`` to pytest and tox.

The test coverage is 100%, patches won't be accepted if not entirely covered. You can check the
test coverage with ``uv run pytest --cov --cov-report=html`` or ``uv run tox -e coverage -- --cov-report=html``.
You can check the HTML coverage report in the newly created `htmlcov` directory.

Code style
----------

We use `ruff <https://docs.astral.sh/ruff/>`_ along with other tools to format our code.
Please run ``uv run tox -e style`` on your patches before submitting them.
In order to perform a style check and correction at each commit you can use our
`pre-commit <https://pre-commit.com/>`_ configuration with ``uv run pre-commit install``.

Front
-----

The interface is built upon the `Fomantic UI <https://fomantic-ui.com/>`_ CSS framework.
The dynamical parts of the interface use `htmx <https://htmx.org/>`_.

- Using Javascript in the interface is tolerated, but the whole website MUST be accessible
  for browsers without Javascript support, and without any feature loss.
- Because of Fomantic UI we have a dependency to jQuery, however new contributions should
  not depend on jQuery at all.
  See the `related issue <https://gitlab.com/yaal/canaille/-/issues/130>`_.

Documentation
-------------

The documentation is generated when the tests run:

.. code-block:: bash

    tox -e doc

You can also run sphinx by hand, that should be faster since it avoids the tox environment initialization:

.. code-block:: bash

   sphinx-build doc build/sphinx/html/en

The generated documentation is located at ``build/sphinx/html/en``.

.. note::

   The documentation generates dynamic screenshots of Canaille using `sphinxcontrib-screenshot`_, that internally uses `Playwright`_.
   Playwright needs to be initialized with the following command:

   .. code-block:: bash

      uv run playwright install firefox

.. _sphinxcontrib-screenshot: https://sphinxcontrib-screenshot.readthedocs.io
.. _Playwright: https://playwright.dev/python

Code translation
----------------

.. include:: ../../canaille/translations/README.rst


Documentation translation
-------------------------

.. include:: ../locales/readme.rst

Production Docker image
-----------------------

Build
~~~~~

The ``nix-build`` command is needed to create the Canaille Docker image.
Follow the `NixOS documentation instructions <https://nix.dev/manual/nix/stable/installation/installing-binary>`__ to install it on your system.

The Docker image can be built with the following command:

.. code-block:: bash

   docker load < $(nix-build --no-out-link canaille.nix)

Check the Docker image with the following command:

.. code-block:: bash

   docker run -it -p 5000:5000 canaille:latest

Publish
~~~~~~~

.. code-block:: bash

    export CANAILLE_VERSION=$(python -c "from importlib.metadata import version; print(version('canaille'))")
    docker tag canaille:latest "yaalcoop/canaille:latest"
    docker tag canaille:latest "yaalcoop/canaille:${CANAILLE_VERSION}"

    docker login --username <hub docker login>
    docker push yaalcoop/canaille:latest
    docker push yaalcoop/canaille:${CANAILLE_VERSION}

Use
~~~

.. code-block:: bash

    docker pull yaalcoop/canaille:latest

Build a release
---------------

Python package
~~~~~~~~~~~~~~

The Python packaging step is took care of by uv:

.. code-block:: bash

    uv build

Binary file
~~~~~~~~~~~

To build a single binary of Canaille, you can use pyinstaller by installing the `release` dependency group:

.. code-block:: bash

    uv sync --group release --all-extras --no-dev
    uv run pyinstaller canaille.spec

Publish a new release
---------------------

1. Check that dependencies are up to date with ``uv sync --all-extras --all-groups --upgrade`` and update dependencies accordingly in separated commits;
2. Check that tests are still green for every supported python version, and that coverage is still at 100%, by running ``uv run tox``;
3. Check that the development environments are still working, both the local and the Docker one;
4. Check that the :ref:`development/changelog:Release notes` section is correctly filled up;
5. Increase the version number in ``pyproject.toml``;
6. Commit with ``git commit``;
7. :ref:`Build the packages <development/contributing:Build a release>` with ``uv build``;
8. Install from the .whl generated with ``uv pip install <path/to/dist/canaille-x.x.xx-py3-none-any.whl>[front,oidc,postgresql,server,otp,sms]``;
9. Test creation of a user with ``canaille config dump`` and ``canaille create user --user-name admin --password admin --emails admin@mydomain.example --given-name George --family-name Abitbol`` and ``canaille run``;
10. Try to connect the user;
11. Publish the Python package on test PyPI with ``uv publish --publish-url https://test.pypi.org/legacy/``;
12. Install the test package somewhere with ``pip install --extra-index-url https://test.pypi.org/simple --upgrade "canaille[front,oidc,postgresql,server,otp,sms]"``. Check that everything looks fine;
13. Publish the Python package on production PyPI ``uv publish``;
14. Tag the commit with ``git tag XX.YY.ZZ``;
15. Push the release commit and the new tag on the repository with ``git push --tags``.
16. Try to :ref:`pull and run the docker image of Canaille <development/contributing:Production Docker image>` and update the ``canaille.nix`` file if necessary.
