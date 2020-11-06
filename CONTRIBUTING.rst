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

To try a development environment, you can run the docker image and then open https://127.0.0.1:5000
You can then connect with user *admin* and password *admin* to access an admin account, or user *user* and password *user* for a regular one.

.. code-block:: console

    cp canaille/conf/config.sample.toml canaille/conf/config.toml
    cp canaille/conf/oauth-authorization-server.sample.json canaille/conf/oauth-authorization-server.json
    cp canaille/conf/openid-configuration.sample.json canaille/conf/openid-configuration.json
    cd dev
    docker-compose up
