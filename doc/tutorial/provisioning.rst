Provisioning
############

Canaille partially implement the :rfc:`SCIM <7642>` provisioning protocol at the ``/scim/v2`` endpoint.

At the moment, only the server part is implemented.
It allows client applications to manage user profiles directly in Canaille.

To allow clients to access the SCIM API, the client must have the ``client_credentials`` grant type configured.
This allows clients to ask an authentication token on their own behalf and use this token to perform queries.
Currently, user tokens are not supported.

Then the :attr:`CANAILLE_SCIM.ENABLE_SERVER <canaille.scim.configuration.SCIMSettings.ENABLE_SERVER>` configuration parameter must be enabled.

.. code-block:: toml

   ...
   [CANAILLE_SCIM]
   ENABLE_SERVER = true

.. todo::

   Some SCIM :ref:`features and endpoints <scim_unimplemented>` are not implemented.
   In addition to these, Canaille will implement in the future:

   - Access control for clients on the SCIM API endpoint, to finely manage permissions depending on clients.
   - Client-side implementation, to broadcast user and groups modifications among all the clients.
