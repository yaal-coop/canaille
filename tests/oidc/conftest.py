import datetime
import os
import uuid

import pytest
from authlib.oidc.core.grants.util import generate_id_token
from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Client
from canaille.oidc.models import Consent
from canaille.oidc.models import Token
from canaille.oidc.oauth import generate_user_info
from canaille.oidc.oauth import get_jwt_config
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from werkzeug.security import gen_salt


@pytest.fixture
def app(app):
    os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "true"
    yield app


@pytest.fixture(scope="session")
def keypair():
    key = rsa.generate_private_key(
        backend=crypto_default_backend(), public_exponent=65537, key_size=2048
    )
    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption(),
    )
    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH, crypto_serialization.PublicFormat.OpenSSH
    )
    return private_key, public_key


@pytest.fixture
def keypair_path(keypair, tmp_path):
    private_key, public_key = keypair

    private_key_path = os.path.join(tmp_path, "private.pem")
    with open(private_key_path, "wb") as fd:
        fd.write(private_key)

    public_key_path = os.path.join(tmp_path, "public.pem")
    with open(public_key_path, "wb") as fd:
        fd.write(public_key)

    return private_key_path, public_key_path


@pytest.fixture
def configuration(configuration, keypair_path):
    private_key_path, public_key_path = keypair_path
    conf = {
        **configuration,
        "JWT": {
            "PUBLIC_KEY": public_key_path,
            "PRIVATE_KEY": private_key_path,
            "ISS": "https://auth.mydomain.tld",
            "MAPPING": {
                "SUB": "{{ user.uid[0] }}",
                "NAME": "{{ user.cn[0] }}",
                "PHONE_NUMBER": "{{ user.telephoneNumber[0] }}",
                "EMAIL": "{{ user.mail[0] }}",
                "GIVEN_NAME": "{{ user.givenName[0] }}",
                "FAMILY_NAME": "{{ user.sn[0] }}",
                "PREFERRED_USERNAME": "{{ user.displayName }}",
                "LOCALE": "{{ user.preferredLanguage }}",
                "PICTURE": "{% if user.jpegPhoto %}{{ url_for('account.photo', uid=user.uid[0], field='jpegPhoto', _external=True) }}{% endif %}",
                "ADDRESS": "{{ user.postalAddress[0] }}",
                "WEBSITE": "{{ user.labeledURI[0] }}",
            },
        },
    }
    return conf


@pytest.fixture
def client(testclient, other_client, slapd_connection):
    c = Client(
        client_id=gen_salt(24),
        client_name="Some client",
        contacts="contact@mydomain.tld",
        client_uri="https://mydomain.tld",
        redirect_uris=[
            "https://mydomain.tld/redirect1",
            "https://mydomain.tld/redirect2",
        ],
        logo_uri="https://mydomain.tld/logo.png",
        client_id_issued_at=datetime.datetime.now(),
        client_secret=gen_salt(48),
        grant_types=[
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
        ],
        response_types=["code", "token", "id_token"],
        scope=["openid", "email", "profile", "groups", "address", "phone"],
        tos_uri="https://mydomain.tld/tos",
        policy_uri="https://mydomain.tld/policy",
        jwks_uri="https://mydomain.tld/jwk",
        token_endpoint_auth_method="client_secret_basic",
        post_logout_redirect_uris=["https://mydomain.tld/disconnected"],
    )
    c.audience = [c.dn, other_client.dn]
    c.save()

    yield c
    c.delete()


@pytest.fixture
def other_client(testclient, slapd_connection):
    c = Client(
        client_id=gen_salt(24),
        client_name="Some other client",
        contacts="contact@myotherdomain.tld",
        client_uri="https://myotherdomain.tld",
        redirect_uris=[
            "https://myotherdomain.tld/redirect1",
            "https://myotherdomain.tld/redirect2",
        ],
        logo_uri="https://myotherdomain.tld/logo.png",
        client_id_issued_at=datetime.datetime.now(),
        client_secret=gen_salt(48),
        grant_types=[
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
        ],
        response_types=["code", "token", "id_token"],
        scope=["openid", "profile", "groups"],
        tos_uri="https://myotherdomain.tld/tos",
        policy_uri="https://myotherdomain.tld/policy",
        jwks_uri="https://myotherdomain.tld/jwk",
        token_endpoint_auth_method="client_secret_basic",
        post_logout_redirect_uris=["https://myotherdomain.tld/disconnected"],
    )
    c.audience = [c.dn]
    c.save()

    yield c
    c.delete()


@pytest.fixture
def authorization(testclient, user, client, slapd_connection):
    a = AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code="my-code",
        client=client.dn,
        subject=user.dn,
        redirect_uri="https://foo.bar/callback",
        response_type="code",
        scope="openid profile",
        nonce="nonce",
        issue_date=datetime.datetime(2020, 1, 1),
        lifetime="3600",
        challenge="challenge",
        challenge_method="method",
        revokation="",
    )
    a.save()
    yield a
    a.delete()


@pytest.fixture
def token(testclient, client, user, slapd_connection):
    t = Token(
        token_id=gen_salt(48),
        access_token=gen_salt(48),
        audience=[client.dn],
        client=client.dn,
        subject=user.dn,
        token_type=None,
        refresh_token=gen_salt(48),
        scope="openid profile",
        issue_date=datetime.datetime.now(),
        lifetime=str(3600),
    )
    t.save()
    yield t
    t.delete()


@pytest.fixture
def id_token(testclient, client, user, slapd_connection):
    return generate_id_token(
        {},
        generate_user_info(user.dn, client.scope),
        aud=client.client_id,
        **get_jwt_config(None)
    )


@pytest.fixture
def consent(testclient, client, user, slapd_connection):
    t = Consent(
        cn=str(uuid.uuid4()),
        client=client.dn,
        subject=user.dn,
        scope=["openid", "profile"],
        issue_date=datetime.datetime.now(),
    )
    t.save()
    yield t
    t.delete()
