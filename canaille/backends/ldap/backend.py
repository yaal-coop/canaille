import logging
import uuid

import ldap
from canaille.app.configuration import ConfigurationException
from flask import g
from flask import render_template
from flask import request
from flask_babel import gettext as _


def setup_ldap_models(config):
    from .ldapobject import LDAPObject
    from canaille.core.models import Group
    from canaille.core.models import User

    LDAPObject.root_dn = config["BACKENDS"]["LDAP"]["ROOT_DN"]

    user_base = config["BACKENDS"]["LDAP"]["USER_BASE"].replace(
        f',{config["BACKENDS"]["LDAP"]["ROOT_DN"]}', ""
    )
    User.base = user_base
    User.rdn_attribute = config["BACKENDS"]["LDAP"].get(
        "USER_ID_ATTRIBUTE", User.DEFAULT_ID_ATTRIBUTE
    )
    object_class = config["BACKENDS"]["LDAP"].get(
        "USER_CLASS", User.DEFAULT_OBJECT_CLASS
    )
    User.ldap_object_class = (
        object_class if isinstance(object_class, list) else [object_class]
    )

    group_base = (
        config["BACKENDS"]["LDAP"]
        .get("GROUP_BASE", "")
        .replace(f',{config["BACKENDS"]["LDAP"]["ROOT_DN"]}', "")
    )
    Group.base = group_base or None
    Group.rdn_attribute = config["BACKENDS"]["LDAP"].get(
        "GROUP_ID_ATTRIBUTE", Group.DEFAULT_ID_ATTRIBUTE
    )
    object_class = config["BACKENDS"]["LDAP"].get(
        "GROUP_CLASS", Group.DEFAULT_OBJECT_CLASS
    )
    Group.ldap_object_class = (
        object_class if isinstance(object_class, list) else [object_class]
    )


def setup_backend(app):
    try:  # pragma: no cover
        if request.endpoint == "static":
            return
    except RuntimeError:  # pragma: no cover
        pass

    try:
        g.ldap_connection = ldap.initialize(app.config["BACKENDS"]["LDAP"]["URI"])
        g.ldap_connection.set_option(
            ldap.OPT_NETWORK_TIMEOUT, app.config["BACKENDS"]["LDAP"].get("TIMEOUT")
        )
        g.ldap_connection.simple_bind_s(
            app.config["BACKENDS"]["LDAP"]["BIND_DN"],
            app.config["BACKENDS"]["LDAP"]["BIND_PW"],
        )

    except ldap.SERVER_DOWN:
        message = _("Could not connect to the LDAP server '{uri}'").format(
            uri=app.config["BACKENDS"]["LDAP"]["URI"]
        )
        logging.error(message)
        return (
            render_template(
                "error.html",
                error=500,
                icon="database",
                debug=app.config.get("DEBUG", False),
                description=message,
            ),
            500,
        )

    except ldap.INVALID_CREDENTIALS:
        message = _("LDAP authentication failed with user '{user}'").format(
            user=app.config["BACKENDS"]["LDAP"]["BIND_DN"]
        )
        logging.error(message)
        return (
            render_template(
                "error.html",
                error=500,
                icon="key",
                debug=app.config.get("DEBUG", False),
                description=message,
            ),
            500,
        )


def teardown_backend(app):
    if g.get("ldap_connection"):  # pragma: no branch
        g.ldap_connection.unbind_s()
        g.ldap_connection = None


def init_backend(app):
    setup_ldap_models(app.config)

    @app.before_request
    def before_request():
        if not app.config["TESTING"]:
            return setup_backend(app)

    @app.after_request
    def after_request(response):
        if not app.config["TESTING"]:
            teardown_backend(app)
        return response


def validate_configuration(config):
    from canaille.core.models import Group
    from canaille.core.models import User

    try:
        conn = ldap.initialize(config["BACKENDS"]["LDAP"]["URI"])
        conn.set_option(
            ldap.OPT_NETWORK_TIMEOUT, config["BACKENDS"]["LDAP"].get("TIMEOUT")
        )
        conn.simple_bind_s(
            config["BACKENDS"]["LDAP"]["BIND_DN"], config["BACKENDS"]["LDAP"]["BIND_PW"]
        )

    except ldap.SERVER_DOWN as exc:
        raise ConfigurationException(
            f'Could not connect to the LDAP server \'{config["BACKENDS"]["LDAP"]["URI"]}\''
        ) from exc

    except ldap.INVALID_CREDENTIALS as exc:
        raise ConfigurationException(
            f'LDAP authentication failed with user \'{config["BACKENDS"]["LDAP"]["BIND_DN"]}\''
        ) from exc

    try:
        User.ldap_object_classes(conn)
        user = User(
            formatted_name=f"canaille_{uuid.uuid4()}",
            family_name=f"canaille_{uuid.uuid4()}",
            user_name=f"canaille_{uuid.uuid4()}",
            email=f"canaille_{uuid.uuid4()}@mydomain.tld",
            password="correct horse battery staple",
        )
        user.save(conn)
        user.delete(conn)

    except ldap.INSUFFICIENT_ACCESS as exc:
        raise ConfigurationException(
            f'LDAP user \'{config["BACKENDS"]["LDAP"]["BIND_DN"]}\' cannot create '
            f'users at \'{config["BACKENDS"]["LDAP"]["USER_BASE"]}\''
        ) from exc

    try:
        Group.ldap_object_classes(conn)

        user = User(
            cn=f"canaille_{uuid.uuid4()}",
            family_name=f"canaille_{uuid.uuid4()}",
            user_name=f"canaille_{uuid.uuid4()}",
            email=f"canaille_{uuid.uuid4()}@mydomain.tld",
            password="correct horse battery staple",
        )
        user.save(conn)

        group = Group(
            display_name=f"canaille_{uuid.uuid4()}",
            members=[user],
        )
        group.save(conn)
        group.delete(conn)

    except ldap.INSUFFICIENT_ACCESS as exc:
        raise ConfigurationException(
            f'LDAP user \'{config["BACKENDS"]["LDAP"]["BIND_DN"]}\' cannot create '
            f'groups at \'{config["BACKENDS"]["LDAP"]["GROUP_BASE"]}\''
        ) from exc

    finally:
        user.delete(conn)

    conn.unbind_s()
