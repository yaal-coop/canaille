Provisioning
############

Canaille partially implement the :rfc:`SCIM <7642>` provisioning protocol, so user and group modifications can be spread across an entire application ecosystem.

Provisioning server
===================

Canaille acts as a provisioning server.
This means that client applications can perform requests on the ``/scim/v2`` endpoint, using the SCIM2 protocol, to manage user and group objects.

Provisioning client
===================

Canaille also acts a provisioning client.
This means that all modifications on user and groups are spread among the client applications implementing the SCIM2 server specification.
This ensures that the details of users and groups are always synchronized among all your client applications.

Modifications are sent to client applications whether they come from the :ref:`web interface <feature_profile_management>`, the :ref:`CLI <references/commands:Command Line Interface>` or from another client application requesting the Canaille SCIM server endpoint.

Canaille will attempt to authenticate against the client SCIM2 server endpoint with a Bearer token it has emitted on behalf of the client.
Please make sure that your client application is properly configured to accept Canaille tokens.

.. warning::

   Note that the SCIM client feature is at early development stage and comes with poor performances at the moment.

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

Then the :attr:`CANAILLE_SCIM.ENABLE_SERVER <canaille.scim.configuration.SCIMSettings.ENABLE_SERVER>`
configuration parameter must be enabled.

.. code-block:: toml

   ...
   [CANAILLE_SCIM]
   ENABLE_SERVER = true

To allow Canaille to act as a SCIM client and broadcast modifications to client applications,
the :attr:`CANAILLE_SCIM.ENABLE_CLIENT <canaille.scim.configuration.SCIMSettings.ENABLE_CLIENT>`
configuration parameter must be enabled.


.. code-block:: toml

   ...
   [CANAILLE_SCIM]
   ENABLE_CLIENT = true

Implementation details
======================

Due to technical reasons, the server-side Canaille *User* and *Group* resources implementation subtly differs from the :rfc:`RFC7643 <7643>` definitions:

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
