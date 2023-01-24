import logging
import uuid

import ldap
from canaille.configuration import ConfigurationException
from flask import g
from flask import render_template
from flask import request
from flask_babel import gettext as _


def setup_ldap_models(config):
    from .ldapobject import LDAPObject
    from ..models import Group
    from ..models import User

    LDAPObject.root_dn = config["LDAP"]["ROOT_DN"]

    user_base = config["LDAP"]["USER_BASE"].replace(f',{config["LDAP"]["ROOT_DN"]}', "")
    User.base = user_base
    User.rdn = config["LDAP"].get("USER_ID_ATTRIBUTE", User.DEFAULT_ID_ATTRIBUTE)
    User.object_class = [config["LDAP"].get("USER_CLASS", User.DEFAULT_OBJECT_CLASS)]

    group_base = (
        config["LDAP"]
        .get("GROUP_BASE", "")
        .replace(f',{config["LDAP"]["ROOT_DN"]}', "")
    )
    Group.base = group_base or None
    Group.rdn = config["LDAP"].get("GROUP_ID_ATTRIBUTE", Group.DEFAULT_ID_ATTRIBUTE)
    Group.object_class = [config["LDAP"].get("GROUP_CLASS", Group.DEFAULT_OBJECT_CLASS)]


def setup_backend(app):
    try:  # pragma: no cover
        if request.endpoint == "static":
            return
    except RuntimeError:  # pragma: no cover
        pass

    try:
        g.ldap = ldap.initialize(app.config["LDAP"]["URI"])
        g.ldap.set_option(ldap.OPT_NETWORK_TIMEOUT, app.config["LDAP"].get("TIMEOUT"))
        g.ldap.simple_bind_s(
            app.config["LDAP"]["BIND_DN"], app.config["LDAP"]["BIND_PW"]
        )

    except ldap.SERVER_DOWN:
        message = _("Could not connect to the LDAP server '{uri}'").format(
            uri=app.config["LDAP"]["URI"]
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
            user=app.config["LDAP"]["BIND_DN"]
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
    if g.get("ldap"):  # pragma: no branch
        g.ldap.unbind_s()
        g.ldap = None


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
    from canaille.models import User, Group

    try:
        conn = ldap.initialize(config["LDAP"]["URI"])
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, config["LDAP"].get("TIMEOUT"))
        conn.simple_bind_s(config["LDAP"]["BIND_DN"], config["LDAP"]["BIND_PW"])

    except ldap.SERVER_DOWN as exc:
        raise ConfigurationException(
            f'Could not connect to the LDAP server \'{config["LDAP"]["URI"]}\''
        ) from exc

    except ldap.INVALID_CREDENTIALS as exc:
        raise ConfigurationException(
            f'LDAP authentication failed with user \'{config["LDAP"]["BIND_DN"]}\''
        ) from exc

    try:
        User.ldap_object_classes(conn)
        user = User(
            cn=f"canaille_{uuid.uuid4()}",
            sn=f"canaille_{uuid.uuid4()}",
            uid=f"canaille_{uuid.uuid4()}",
            mail=f"canaille_{uuid.uuid4()}@mydomain.tld",
            userPassword="{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz",
        )
        user.save(conn)
        user.delete(conn)

    except ldap.INSUFFICIENT_ACCESS as exc:
        raise ConfigurationException(
            f'LDAP user \'{config["LDAP"]["BIND_DN"]}\' cannot create '
            f'users at \'{config["LDAP"]["USER_BASE"]}\''
        ) from exc

    try:
        Group.ldap_object_classes(conn)

        user = User(
            cn=f"canaille_{uuid.uuid4()}",
            sn=f"canaille_{uuid.uuid4()}",
            uid=f"canaille_{uuid.uuid4()}",
            mail=f"canaille_{uuid.uuid4()}@mydomain.tld",
            userPassword="{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz",
        )
        user.save(conn)

        group = Group(
            cn=f"canaille_{uuid.uuid4()}",
            member=[user.dn],
        )
        group.save(conn)
        group.delete(conn)

    except ldap.INSUFFICIENT_ACCESS as exc:
        raise ConfigurationException(
            f'LDAP user \'{config["LDAP"]["BIND_DN"]}\' cannot create '
            f'groups at \'{config["LDAP"]["GROUP_BASE"]}\''
        ) from exc

    finally:
        user.delete(conn)

    conn.unbind_s()
