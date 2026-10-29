Provisioning
############

Canaille partially implement the :rfc:`SCIM <7642>` provisioning protocol, so user and group modifications can be spread across an entire application ecosystem.

Provisioning server
===================

Canaille acts as a provisioning server.
This means that client applications can perform requests on the ``/scim/v2`` endpoint, using the SCIM2 protocol, to manage user and group objects.

Provisioning client
===================

Canaille also acts as a provisioning client.
It sends the user and group modifications to the client applications that implement a SCIM server.
The modifications are sent whether they come from the :ref:`web interface <feature_profile_management>`, the :ref:`CLI <references/commands:Command Line Interface>` or from another client application that uses the Canaille SCIM server.
The :attr:`CANAILLE_SCIM.ENABLE_CLIENT <canaille.scim.configuration.SCIMSettings.ENABLE_CLIENT>` configuration parameter enables the provisioning client.

.. warning::

   The SCIM client feature is at early development stage and comes with poor performances at the moment.

Provisioned clients
-------------------

Canaille sends a user to these clients:

- the clients the user has given consent to, unless they have :attr:`owners <canaille.oidc.basemodels.Client.owners>`;
- the :attr:`trusted <canaille.oidc.basemodels.Client.trusted>` clients, which receive all the users.

Canaille sends a group to the clients of its members, and to the trusted clients.
The trusted clients also receive the groups without members.
When a :doc:`task worker <worker>` is configured, it sends the user modifications.

SCIM server requirements
------------------------

Canaille uses the :attr:`~canaille.oidc.basemodels.Client.client_uri` of the client as the base URL of its SCIM server.
For instance, with ``https://app.example/scim/v2`` as ``client_uri``, Canaille reads ``https://app.example/scim/v2/ResourceTypes``.
A client without a SCIM server at this URL is skipped.

The SCIM server of the client must:

- publish the ``/ServiceProviderConfig``, ``/ResourceTypes`` and ``/Schemas`` endpoints;
- support :rfc:`filtering <7644#section-3.4.2.2>`, otherwise Canaille does not provision the client;
- store the ``externalId`` attribute and filter on it.

Canaille sets the ``externalId`` of the users and groups to their Canaille ``id``.
Canaille finds the resources of the client with an ``externalId eq "<id>"`` filter, then updates or deletes them.
When the server does not support PATCH, Canaille replaces the resources with PUT.
The password of the users is never sent.

Authentication
--------------

Canaille authenticates against the SCIM server of the client with a Bearer token.
Canaille issues this token for the client itself: the token has the client as audience, has no user, and expires after one hour.
To check the token, the client calls the :rfc:`introspection endpoint <7662>` of Canaille, ``/oauth/introspect``, with its own client credentials.
The introspection response is active while the token is valid.

Troubleshooting
---------------

Canaille logs the provisioning events in the ``canaille`` logger:

.. list-table::
   :header-rows: 1

   * - Level
     - Event
   * - ``INFO``
     - The client has no SCIM server at its ``client_uri``.
   * - ``ERROR``
     - The SCIM server refuses the token with a 401 or 403 response.
   * - ``ERROR``
     - The SCIM server does not support filtering.
   * - ``ERROR``
     - The creation, update or deletion of a user or a group fails.
   * - ``WARNING``
     - A deleted user or group is not found on the client.
   * - ``WARNING``
     - A member of a group is not found on the client.

Configuration
=============

To allow clients to access the SCIM API, the client must have the :ref:`client_credentials <grant_types>` grant type configured.
This allows clients to ask an authentication token on their own behalf and use this token to perform queries.
The client must also have one of these scopes:

- ``scim:users:read`` and ``scim:users:write`` to read or write the users;
- ``scim:groups:read`` and ``scim:groups:write`` to read or write the groups;
- ``scim:read`` and ``scim:write`` to read or write both.

The write scopes also allow reading.

User tokens only give access to the user they belong to,
on the :rfc:`/Me <7644#section-3.11>` endpoint or on ``/Users/<id>``.
They need the ``scim:me`` scope, which users accept on the consent page.
Users can only modify the attributes of their ``WRITE`` :class:`ACL <canaille.core.configuration.ACLSettings>`,
and need the :attr:`~canaille.core.configuration.Permission.EDIT_SELF` permission to edit their account,
and the :attr:`~canaille.core.configuration.Permission.DELETE_ACCOUNT` or :attr:`~canaille.core.configuration.Permission.MANAGE_USERS` permission to delete it.

The ``/ServiceProviderConfig``, ``/ResourceTypes`` and ``/Schemas`` endpoints need no token.

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

The Canaille SCIM server supports :rfc:`bulk operations <7644#section-3.7>`.
The following configuration parameters can be specified regarding bulk operations:

.. code-block:: toml

   ...
   [CANAILLE_SCIM]
   # Maximum number of operations allowed in a bulk request
   BULK_MAX_OPERATIONS = 100
   # Maximum payload size (in bytes) allowed in a bulk request
   BULK_MAX_PAYLOAD_SIZE = 1048576


Implementation details
======================

Due to technical reasons, the server-side Canaille *User* and *Group* resources implementation subtly differs from the :rfc:`RFC7643 <7643>` definitions:

- ``User.userName`` is immutable (while it is read-write in RFC7643), because the OIDC ``sub`` claim uses it by default.
- ``User.name.familyName`` is required (while it is optional in RFC7643).
- ``Group.displayName`` is required (while it is optional in RFC7643).
- ``Group.members`` is required (while it is optional in RFC7643), i.e. groups cannot be empty.

Debugging
=========

To check what data are exposed through the Canaille SCIM API, you need a *client token* and a SCIM client application.
To generate a client token, you can simply manually create a token from the button on the client administration page.
The token gets the scopes of the client, so the client needs one of the SCIM scopes listed above.
Then, we recommend the use of :doc:`scim2-cli:index` to interact with the API:

.. code-block:: console
   :caption: scim2-cli usage example

    $ pip install scim2-cli
    $ export SCIM_CLI_URL="https://canaille.example/scim/v2"
    $ export SCIM_CLI_HEADERS="Authorization: Bearer <MY_CLIENT_TOKEN>"
    $ scim query user 2819c223-7f76-453a-919d-413861904646
    {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
        ],
        "id": "2819c223-7f76-453a-919d-413861904646",
        "meta": {
            "resourceType": "User",
            "created": "2024-12-05T16:08:51.896646Z",
            "lastModified": "2024-12-05T16:08:51.896646Z",
            "location": "https://canaille.example/scim/v2/Users/2819c223-7f76-453a-919d-413861904646",
            "version": "W/\"637b1ce03c010cd55fe45b6f7be2247b5159b135\""
        },
        "userName": "bjensen@example.com"
    }
