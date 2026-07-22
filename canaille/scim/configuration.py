from canaille.app.configuration import BaseModel


class SCIMSettings(BaseModel):
    """SCIM settings."""

    ENABLE_SERVER: bool = True
    """Whether the SCIM server API is enabled.

    When enabled, services plugged to Canaille can update users and groups using the API."""

    ENABLE_CLIENT: bool = False
    """Whether the state of :class:`~canaille.core.models.User` and :class:`~canaille.core.models.Group` are broadcasted to clients using the SCIM protocol.

    When enabled, any creation, edition or deletion of a client or a group will be replicated on clients that implement the SCIM protocol."""

    BULK_MAX_OPERATIONS: int = 100
    """Maximum number of operations allowed in a bulk request."""

    BULK_MAX_PAYLOAD_SIZE: int = 1048576
    """Maximum payload size (in bytes) allowed in a bulk request."""
