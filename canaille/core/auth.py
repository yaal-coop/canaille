import datetime
from dataclasses import dataclass
from functools import wraps

from flask import current_app
from flask import flash
from flask import g
from flask import redirect
from flask import session
from flask import url_for

from canaille.app.i18n import gettext as _
from canaille.app.session import login_user
from canaille.app.session import save_user_session
from canaille.backends import Backend
from canaille.core.models import User

AUTHENTICATION_FACTORS = {}


def auth_step(step_name=None):
    """Decorate authentication steps and perform basic checks."""

    def wrapper(view_function):
        AUTHENTICATION_FACTORS[step_name] = view_function

        @wraps(view_function)
        def decorator(*args, **kwargs):
            if not g.auth:
                if g.session:
                    return redirect(url_for("core.account.index"))

                flash(
                    _("Cannot remember the login you attempted to sign in with."),
                    "warning",
                )
                return redirect(url_for("core.auth.login"))

            if (
                isinstance(g.auth.current_step, str)
                and step_name != g.auth.current_step
            ) or (
                isinstance(g.auth.current_step, list)
                and step_name not in g.auth.current_step
            ):
                return redirect_to_next_auth_step()

            return view_function(*args, **kwargs)

        return decorator

    return wrapper


@dataclass
class AuthenticationSession:
    user_name: str
    """The user name attempting to log-in."""

    remaining: list[str]
    """The remaining auth factors to succeed before logging in."""

    achieved: list[str]
    """The achieved auth factors."""

    current_step_start_dt: datetime.datetime
    """The time when the current step has been started."""

    current_step_try_dt: datetime.datetime
    """The time when the current try of the current step has started."""

    welcome_flash: bool
    """Display a welcom flash when users are logged in."""

    data: dict[str, str]
    """Custom auth factor data."""

    _user: User | None = None

    def __init__(
        self,
        user_name,
        remaining=None,
        achieved=None,
        current_step_start_dt=None,
        current_step_try_dt=None,
        welcome_flash=None,
        data=None,
    ):
        self.user_name = user_name
        self.remaining = (
            remaining or current_app.config["CANAILLE"]["AUTHENTICATION_FACTORS"]
        )
        self.achieved = achieved or []
        self.current_step_start_dt = current_step_start_dt or None
        self.current_step_try_dt = current_step_try_dt or None
        self.data = data or {}
        self.welcome_flash = welcome_flash if welcome_flash is not None else True

    def serialize(self):
        payload = {
            "user_name": self.user_name,
            "welcome_flash": self.welcome_flash,
            "remaining": self.remaining,
        }

        if self.current_step_start_dt:
            payload["current_step_start_dt"] = self.current_step_start_dt.isoformat()

        if self.current_step_try_dt:
            payload["current_step_try_dt"] = self.current_step_try_dt.isoformat()

        if self.achieved:
            payload["achieved"] = self.achieved

        if self.data:
            payload["data"] = self.data

        return payload

    @classmethod
    def deserialize(cls, payload):
        if "current_step_start_dt" in payload:
            payload["current_step_start_dt"] = datetime.datetime.fromisoformat(
                payload["current_step_start_dt"]
            )

        if "current_step_try_dt" in payload:
            payload["current_step_try_dt"] = datetime.datetime.fromisoformat(
                payload["current_step_try_dt"]
            )

        return cls(**payload)

    @classmethod
    def load(cls):
        if "auth" in session:
            return AuthenticationSession.deserialize(session.pop("auth"))

    def save(self):
        session["auth"] = self.serialize()

    @property
    def current_step(self):
        return self.remaining[0] if self.remaining else None

    @property
    def user(self):
        if not self._user:
            self._user = (
                g.session.user if g.session else get_user_from_login(self.user_name)
            )
        return self._user

    def set_step_started(self):
        self.current_step_start_dt = datetime.datetime.now(datetime.timezone.utc)
        self.current_step_try_dt = self.current_step_start_dt

    def set_step_finished(self, step):
        self.achieved.append(step)
        self.remaining.pop(0)


def redirect_to_next_auth_step():
    if not g.auth.remaining:
        if g.session:
            g.session.last_login_datetime = datetime.datetime.now(datetime.timezone.utc)
            save_user_session()
        else:
            login_user(g.auth.user)

        redirection = session.pop("redirect-after-login", None)
        if g.auth.welcome_flash and not redirection:
            flash(
                _("Connection successful. Welcome %(user)s", user=g.session.user.name),
                "success",
            )

        current_app.logger.security(f"Successful authentication for {g.auth.user_name}")

        del g.auth
        return redirect(redirection or url_for("core.account.index"))

    try:
        func = AUTHENTICATION_FACTORS[g.auth.current_step]
    except KeyError:
        del g.auth
        flash(
            _(
                "An error happened during your authentication process. Please try again."
            ),
            "error",
        )
        return redirect(url_for("core.auth.login"))

    g.auth.set_step_started()
    return redirect(url_for(f"core.auth.{g.auth.current_step}.{func.__name__}"))


def get_user_from_login(login=None):
    from canaille.app import models

    login_attributes = current_app.config["CANAILLE"]["LOGIN_ATTRIBUTES"]

    if isinstance(login_attributes, list):
        for attr_name in login_attributes:
            if user := Backend.instance.get(models.User, **{attr_name: login}):
                return user

    if isinstance(login_attributes, dict):
        for attr_name, template in login_attributes.items():
            login_value = current_app.jinja_env.from_string(template).render(
                login=login
            )
            if user := Backend.instance.get(models.User, **{attr_name: login_value}):
                return user

    return None


def login_placeholder():
    """Build a placeholder string for the login form, based on the attributes users can use to identify themselves."""
    default_values = {
        "formatted_name": _("John Doe"),
        "user_name": _("jdoe"),
        "emails": _("john.doe@example.com"),
    }
    placeholders = [
        default_values[attr_name]
        for attr_name in current_app.config["CANAILLE"]["LOGIN_ATTRIBUTES"]
        if default_values.get(attr_name)
    ]
    return _(" or ").join(placeholders)
