import datetime
import os
from unittest import mock

import pytest
from babel.messages.frontend import compile_catalog
from flask_webtest import TestApp
from jinja2 import FileSystemBytecodeCache
from jinja2 import StrictUndefined
from pytest_lazy_fixtures import lf
from werkzeug.security import gen_salt

from canaille import create_app
from canaille.app import models
from canaille.app.session import UserSession
from canaille.backends import available_backends


@pytest.fixture(autouse=True, scope="session")
def babel_catalogs():
    cmd = compile_catalog()
    cmd.directory = os.path.dirname(__file__) + "/../canaille/translations"
    cmd.quiet = True
    cmd.statistics = True
    cmd.finalize_options()
    cmd.run()


pytest_plugins = [
    f"tests.backends.{backend}.fixtures"
    for backend in available_backends()
    if os.path.exists(os.path.join("tests", "backends", backend, "fixtures.py"))
]


def pytest_addoption(parser):
    parser.addoption(
        "--backend", action="append", default=[], help="the backends to test"
    )


def pytest_generate_tests(metafunc):
    backends = available_backends()
    if metafunc.config.getoption("backend"):  # pragma: no cover
        backends &= set(metafunc.config.getoption("backend"))

    # sort so the backend list is deterministic. This makes pytest-xdist discovery possible
    backends = sorted(backends)

    # tests in tests.backends.BACKENDNAME should only run one backend
    module_name_parts = metafunc.module.__name__.split(".")
    if module_name_parts[0:2] == ["tests", "backends"] and len(module_name_parts) > 3:
        backend = module_name_parts[2]
        if backend not in backends:  # pragma: no cover
            pytest.skip()
        elif "backend" in metafunc.fixturenames:
            metafunc.parametrize("backend", [lf(f"{backend}_backend")])
            return

    elif "backend" in metafunc.fixturenames:
        metafunc.parametrize(
            "backend",
            [lf(f"{backend}_backend") for backend in backends],
        )


@pytest.fixture
def configuration(smtpd):
    smtpd.config.use_starttls = True
    conf = {
        "SECRET_KEY": gen_salt(24),
        "SERVER_NAME": "canaille.test",
        "PREFERRED_URL_SCHEME": "http",
        "TRUSTED_HOSTS": [".canaille.test", "localhost", ".foobar.test"],
        "TESTING": True,
        "CANAILLE": {
            "JAVASCRIPT": False,
            "TIMEZONE": "UTC",
            "ACL": {
                "DEFAULT": {
                    "READ": ["user_name", "groups"],
                    "PERMISSIONS": ["edit_self", "use_oidc"],
                    "WRITE": [
                        "emails",
                        "given_name",
                        "photo",
                        "family_name",
                        "display_name",
                        "password",
                        "phone_numbers",
                        "formatted_address",
                        "street",
                        "postal_code",
                        "locality",
                        "region",
                        "employee_number",
                        "department",
                        "preferred_language",
                        "title",
                        "organization",
                        "lock_date",
                    ],
                },
                "ADMIN": {
                    "FILTER": [{"user_name": "admin"}, {"family_name": "admin"}],
                    "PERMISSIONS": [
                        "manage_users",
                        "manage_groups",
                        "manage_oidc",
                        "delete_account",
                        "impersonate_users",
                    ],
                    "WRITE": [
                        "groups",
                        "lock_date",
                    ],
                },
                "MODERATOR": {
                    "FILTER": [
                        {"user_name": "moderator"},
                        {"family_name": "moderator"},
                    ],
                    "PERMISSIONS": ["manage_users", "manage_groups", "delete_account"],
                    "WRITE": [
                        "groups",
                    ],
                },
            },
            "SMTP": {
                "HOST": smtpd.hostname,
                "PORT": smtpd.port,
                "TLS": smtpd.config.use_starttls,
                "SSL": smtpd.config.use_ssl,
                "LOGIN": smtpd.config.login_username,
                "PASSWORD": smtpd.config.login_password,
                "FROM_ADDR": "admin@mydomain.test",
            },
            "SMPP": {
                "HOST": "localhost",
                "PORT": 2775,
                "LOGIN": "user",
                "PASSWORD": "user",
            },
            "LOGGING": {
                "version": 1,
                "formatters": {
                    "default": {
                        "format": "[%(asctime)s] - %(levelname)s in %(module)s: %(message)s",
                    },
                    "wsgi": {
                        "format": "[%(asctime)s] - %(ip)s - %(levelname)s in %(module)s: %(message)s",
                    },
                },
                "handlers": {
                    "default": {
                        "class": "logging.StreamHandler",
                        "stream": "ext://sys.stdout",
                        "formatter": "default",
                    },
                    "wsgi": {
                        "class": "logging.StreamHandler",
                        "stream": "ext://sys.stdout",
                        "formatter": "wsgi",
                    },
                },
                "loggers": {
                    "faker": {"level": "WARNING"},
                    "httpx": {"level": "WARNING"},
                    "httpcore": {"level": "WARNING"},
                    "canaille": {"level": "DEBUG", "handlers": ["wsgi"]},
                },
                "disable_existing_loggers": False,
            },
            "ADMIN_EMAIL": "admin_default_mail@mydomain.test",
            "PASSWORD_COMPROMISSION_CHECK_API_URL": "https://api.pwnedpasswords.test/range/",
        },
    }
    return conf


@pytest.fixture(autouse=True)
def email_validator():
    import email_validator

    email_validator.TEST_ENVIRONMENT = True


@pytest.fixture(scope="session")
def jinja_cache_directory(tmp_path_factory):
    return tmp_path_factory.mktemp("cache")


@pytest.fixture
def app(configuration, backend, jinja_cache_directory):
    app = create_app(configuration, backend=backend)
    # caches the Jinja compiled files for faster unit test execution
    app.jinja_env.bytecode_cache = FileSystemBytecodeCache(jinja_cache_directory)

    with app.app_context():
        backend.install(app)

    with app.test_request_context():
        yield app


@pytest.fixture
def testclient(app):
    app.jinja_env.undefined = StrictUndefined
    yield TestApp(app)


@pytest.fixture
def cli_runner(app):
    return app.test_cli_runner(catch_exceptions=False)


@pytest.fixture
def user(app, backend):
    u = models.User(
        formatted_name="John (johnny) Doe",
        given_name="John",
        family_name="Doe",
        user_name="user",
        emails=["john@doe.test"],
        password="correct horse battery staple",
        display_name="Johnny",
        preferred_language="en",
        phone_numbers=["555-000-000"],
        profile_url="https://john.test",
        formatted_address="1234, some street, 6789 some city, some state",
        street="1234, some street",
        locality="some city",
        postal_code="6789",
        region="some state",
        secret_token="fefe9b10",
        hotp_counter=1,
        last_otp_login=datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
    )
    backend.save(u)
    yield u
    backend.delete(u)


@pytest.fixture
def admin(app, backend):
    u = models.User(
        formatted_name="Jane Doe",
        family_name="Doe",
        user_name="admin",
        emails=["jane@doe.test"],
        password="admin",
    )
    backend.save(u)
    yield u
    backend.delete(u)


@pytest.fixture
def moderator(app, backend):
    u = models.User(
        formatted_name="Jack Doe",
        family_name="Doe",
        user_name="moderator",
        emails=["jack@doe.test"],
        password="moderator",
    )
    backend.save(u)
    yield u
    backend.delete(u)


@pytest.fixture
def logged_user(user, testclient):
    with testclient.session_transaction() as sess:
        sess["sessions"] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize()
        ]
    return user


@pytest.fixture
def logged_admin(admin, testclient):
    with testclient.session_transaction() as sess:
        sess["sessions"] = [
            UserSession(
                user=admin,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize()
        ]
    return admin


@pytest.fixture
def logged_moderator(moderator, testclient):
    with testclient.session_transaction() as sess:
        sess["sessions"] = [
            UserSession(
                user=moderator,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize()
        ]
    return moderator


@pytest.fixture
def foo_group(app, user, backend):
    group = models.Group(
        members=[user],
        display_name="foo",
    )
    backend.save(group)
    backend.reload(user)
    yield group
    backend.delete(group)


@pytest.fixture
def bar_group(app, admin, backend):
    group = models.Group(
        members=[admin],
        display_name="bar",
    )
    backend.save(group)
    backend.reload(admin)
    yield group
    backend.delete(group)


@pytest.fixture
def jpeg_photo():
    with open("tests/fixtures/minimal.jpg", "rb") as fd:
        return fd.read()


@pytest.fixture(autouse=True)
def smpp_client():
    client = mock.Mock()
    client.__enter__ = client.Mock()
    client.__exit__ = client.Mock()
    client.__enter__.return_value = client
    with mock.patch("smpplib.client.Client", return_value=client):
        yield client
