Contribute
==========

Contributions are welcome!

Unit tests
----------

To run the tests, you just need to run `tox`. Everything must be green before patches get merged.

Style
-----

We use `black` to format our code. Please apply `black` on your patches before submiting them.

Development environment
-----------------------

To try a development environment, you can run the docker image and then open https://127.0.0.1:5000 to access the canaille server.
Two dummy clients are available at https://127.0.0.1:5001 and https://127.0.0.1:5002
You can then connect with user *admin* and password *admin* to access an admin account, or user *user* and password *user* for a regular one.

.. code-block:: console

    cd demo
    ./run.sh
    # or 'docker-compose up' if you prefer docker
