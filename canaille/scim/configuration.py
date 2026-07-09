from canaille.app.configuration import BaseModel


class SCIMSettings(BaseModel):
    """SCIM settings."""

    ENABLE_SERVER: bool = True
    """Whether the SCIM server API is enabled.

    When enabled, services plugged to Canaille can update users and groups using the API."""

    ENABLE_CLIENT: bool = False
    """Whether the state of :class:`~canaille.core.models.User` and :class:`~canaille.core.models.Group` are broadcasted to clients using the SCIM protocol.

    When enabled, any creation, edition or deletion of a client or a group will be replicated on clients that implement the SCIM protocol."""

    DEFAULT_PAGE_SIZE: int = 20
    """Positive integer value specifying the default number of results returned in a page when a count is not specified in the query."""

    MAX_PAGE_SIZE: int = 100
    """Positive integer specifying the maximum number of results returned in a page regardless of what is specified for the count in a query. The maximum number of results returned may be further restricted by other criteria."""

    CURSOR_TIMEOUT: int = 600
    """Positive integer specifying the minimum number of seconds that a cursor is valid between page requests. Clients waiting too long between cursor pagination requests may receive an invalid cursor error response. No value being specified may mean that there is no cursor timeout or that the cursor timeout is not a static duration."""

