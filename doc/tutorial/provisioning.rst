Provisioning
############

Canaille partially implement the :rfc:`SCIM <7642>` provisioning protocol at the ``/scim/v2`` endpoint.

At the moment, only the server part is implemented.
It allows client applications to manage user profiles directly in Canaille.

.. todo::

   Some SCIM :ref:`features and endpoints <scim_unimplemented>` are not implemented.
   In addition to these, Canaille will implement in the future:

   - Access control for clients on the SCIM API endpoint, to finely manage permissions depending on clients.
   - Client-side implementation, to broadcast user and groups modifications among all the clients.

Configuration
=============

To allow clients to access the SCIM API, the client must have the ``client_credentials`` grant type configured.
This allows clients to ask an authentication token on their own behalf and use this token to perform queries.
Currently, user tokens are not supported.

Then the :attr:`CANAILLE_SCIM.ENABLE_SERVER <canaille.scim.configuration.SCIMSettings.ENABLE_SERVER>` configuration parameter must be enabled.

.. code-block:: toml

   ...
   [CANAILLE_SCIM]
   ENABLE_SERVER = true

Implementation details
======================

Due to technical reasons, the Canaille *User* and *Group* resources implementation subtly differs from the :rfc:`RFC7643 <7643>` definitions:

- ``User.userName`` is immutable (while it is read-write in RFC7643).
- ``User.name.familyName`` is required (while it is optional in RFC7643).
- ``Group.displayName`` is required (while it is optional in RFC7643).
- ``Group.members`` is required (while it is optional in RFC7643), i.e. groups cannot be empty.

Debugging
=========

To check what data are exposed through the Canaille SCIM API, you need a *client token* and a SCIM client application.
To generate a client token, you can simply manually create a token from the button on the client administration page.
Then, we recommend the use of :doc:`scim2-cli:index` to interact with the API:

.. code-block:: console
   :caption: scim2-cli usage example

    $ pip install scim2-cli
    $ export SCIM_CLI_URL="https://canaille.example/scim/v2"
    $ export SCIM_CLI_HEADERS="Authorization: Bearer <MY_CLIENT_TOKEN>"
    $ scim query user bjensen
    {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
        ],
        "id": "bjensen",
        "meta": {
            "resourceType": "User",
            "created": "2024-12-05T16:08:51.896646Z",
            "lastModified": "2024-12-05T16:08:51.896646Z",
            "location": "http://scim.example/v2/Users/bjensen",
            "version": "W/\"637b1ce03c010cd55fe45b6f7be2247b5159b135\""
        },
        "userName": "bjensen@example.com"
    }
