from pydantic import BaseModel


class SCIMSettings(BaseModel):
    """SCIM settings."""

    ENABLE_SERVER: bool = True
