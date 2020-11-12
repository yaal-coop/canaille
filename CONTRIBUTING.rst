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

.. code-block:: console

    cd demo
    ./run.sh

Then you have access to:

- A canaille server at http://127.0.0.1:5000
- A dummy client at http://127.0.0.1:5001
- Another dummy client at http://127.0.0.1:5002

The canaille server has some default users:

- A regular user which login and password are **user**;
- A moderator user which login and password are **moderator**;
- An admin user which admin and password are **admin**.
