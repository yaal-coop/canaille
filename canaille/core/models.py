import datetime
from typing import List
from typing import Optional


class User:
    """
    User model, based on the `SCIM User schema <https://datatracker.ietf.org/doc/html/rfc7643#section-4.1>`_
    """

    id: str
    user_name: Optional[str]
    password: Optional[str]
    preferred_language: Optional[str]
    family_name: Optional[str]
    given_name: Optional[str]
    formatted_name: Optional[str]
    display_name: Optional[str]
    emails: List[str]
    phone_numbers: List[str]
    formatted_address: Optional[str]
    street: Optional[str]
    postal_code: Optional[str]
    locality: Optional[str]
    region: Optional[str]
    photo: Optional[str]
    profile_url: Optional[str]
    employee_number: Optional[str]
    department: Optional[str]
    title: Optional[str]
    organization: Optional[str]
    last_modified: Optional[datetime.datetime]
    groups: List["Group"]
    lock_date: Optional[datetime.datetime]

    def __init__(self, *args, **kwargs):
        self.read = set()
        self.write = set()
        self.permissions = set()
        super().__init__(*args, **kwargs)

    @classmethod
    def get_from_login(cls, login=None, **kwargs) -> Optional["User"]:
        raise NotImplementedError()

    def has_password(self) -> bool:
        """
        Checks wether a password has been set for the user.
        """
        raise NotImplementedError()

    def check_password(self, password: str) -> bool:
        """
        Checks if the password matches the user password in the database.
        """
        raise NotImplementedError()

    def set_password(self, password: str):
        """
        Sets a password for the user.
        """
        raise NotImplementedError()

    def can_read(self, field: str):
        return field in self.read | self.write

    @property
    def preferred_email(self):
        return self.emails[0] if self.emails else None

    def __getattr__(self, name):
        if name.startswith("can_") and name != "can_read":
            permission = name[4:]
            return permission in self.permissions

        return super().__getattr__(name)

    @property
    def locked(self) -> bool:
        """
        Wether the user account has been locked or has expired.
        """
        return bool(self.lock_date) and self.lock_date < datetime.datetime.now(
            datetime.timezone.utc
        )


class Group:
    """
    User model, based on the `SCIM Group schema <https://datatracker.ietf.org/doc/html/rfc7643#section-4.2>`_
    """

    id: str
    display_name: str
    members: List["User"]
    description: Optional[str]
