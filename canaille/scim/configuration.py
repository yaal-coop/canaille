from canaille.app.configuration import BaseModel


class SCIMSettings(BaseModel):
    """SCIM settings."""

    ENABLE_SERVER: bool = True
    """Whether the SCIM server API is enabled.

    When enabled, services plugged to Canaille can update users and groups using the API."""

    ENABLE_CLIENT: bool = False
    """Whether the state of :class:`~canaille.core.models.User` and :class:`~canaille.core.models.Group` are broadcasted to clients using the SCIM protocol.

    When enabled, any creation, edition or deletion of a client or a group will be replicated on clients that implement the SCIM protocol."""
