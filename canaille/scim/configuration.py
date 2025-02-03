from canaille.app.configuration import BaseModel


class SCIMSettings(BaseModel):
    """SCIM settings."""

    ENABLE_SERVER: bool = True
    """Whether the SCIM server API is enabled.

    When enabled, services plugged to Canaille can update users and groups using the API."""
