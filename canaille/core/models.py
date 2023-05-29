import datetime

from flask import session


class User:
    def __init__(self, *args, **kwargs):
        self.read = set()
        self.write = set()
        self.permissions = set()
        super().__init__(*args, **kwargs)

    @classmethod
    def get_from_login(cls, login=None, **kwargs):
        raise NotImplementedError()

    def login(self):
        try:
            previous = (
                session["user_id"]
                if isinstance(session["user_id"], list)
                else [session["user_id"]]
            )
            session["user_id"] = previous + [self.id]
        except KeyError:
            session["user_id"] = [self.id]

    @classmethod
    def logout(self):
        try:
            session["user_id"].pop()
            if not session["user_id"]:
                del session["user_id"]
        except (IndexError, KeyError):
            pass

    def has_password(self):
        raise NotImplementedError()

    def check_password(self, password):
        raise NotImplementedError()

    def set_password(self, password):
        raise NotImplementedError()

    def can_read(self, field):
        return field in self.read | self.write

    @property
    def can_edit_self(self):
        return "edit_self" in self.permissions

    @property
    def can_use_oidc(self):
        return "use_oidc" in self.permissions

    @property
    def can_manage_users(self):
        return "manage_users" in self.permissions

    @property
    def can_manage_groups(self):
        return "manage_groups" in self.permissions

    @property
    def can_manage_oidc(self):
        return "manage_oidc" in self.permissions

    @property
    def can_delete_account(self):
        return "delete_account" in self.permissions

    @property
    def can_impersonate_users(self):
        return "impersonate_users" in self.permissions

    @property
    def locked(self):
        return bool(self.lock_date) and self.lock_date < datetime.datetime.now(
            datetime.timezone.utc
        )


class Group:
    pass
