Contribute
==========

Contributions are welcome!

The repository is hosted at https://gitlab.com/yaal/canaille

.. warning ::

    On Debian or Ubuntu systems, the OpenLDAP `slapd` binary usage might be restricted by apparmor,
    and thus makes the tests and the demo fail. This can be mitigated by removing apparmor restrictions
    on `slapd`.

    .. code-block:: console

        sudo apt install --yes apparmor-utils
        sudo aa-complain /usr/sbin/slapd

Unit tests
----------

To run the tests, you just need to run `tox`. Everything must be green before patches get merged.

The test coverage is 100%, patches won't be accepted if not entirely covered.

Style
-----

We use `black` to format our code. Please apply `black` on your patches before submiting them.

Development environment
-----------------------

.. code-block:: console

    python3 setup.py compile_catalog
    cd demo
    ./run.sh # or `docker-compose up` to run it with docker

Then you have access to:

- A canaille server at http://localhost:5000
- A dummy client at http://localhost:5001
- Another dummy client at http://localhost:5002

The canaille server has some default users:

- A regular user which login and password are **user**;
- A moderator user which login and password are **moderator**;
- An admin user which admin and password are **admin**.


Documentation
-------------


The documentation is generated when the tests run:

.. code-block:: console

    tox -e doc

The generated documentation is in `./build/sphinx/html/` directory.

Translation
-----------

Translations are done with `Weblate <https://hosted.weblate.org/engage/canaille/>`_
