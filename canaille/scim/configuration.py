from canaille.app.configuration import BaseModel


class SCIMSettings(BaseModel):
    """SCIM settings."""

    ENABLE_SERVER: bool = True
