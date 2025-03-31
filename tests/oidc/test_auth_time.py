import datetime
from urllib.parse import parse_qs
from urllib.parse import urlsplit

import time_machine

from canaille.app import models

from . import client_credentials


def test_nominal_case(testclient, user, client, keypair, trusted_client, backend):
    max_age = int(datetime.timedelta(hours=3).total_seconds())

    with time_machine.travel("2025-01-01 02:30:00+00:00", tick=False):
        res = testclient.get("/login")

        res.form["login"] = "user"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

    with time_machine.travel("2025-01-01 03:00:00+00:00", tick=False):
        res = testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type="code",
                client_id=client.client_id,
                scope="openid",
                nonce="somenonce",
                redirect_uri="https://client.test/redirect1",
                max_age=max_age,
            ),
        )
        res = res.form.submit(name="answer", value="accept", status=302)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]

    with time_machine.travel("2025-01-01 03:01:00+00:00", tick=False):
        res = testclient.post(
            "/oauth/token",
            params=dict(
                grant_type="authorization_code",
                code=code,
                scope="openid",
                redirect_uri=client.redirect_uris[0],
            ),
            headers={"Authorization": f"Basic {client_credentials(client)}"},
        )

    for consent in backend.query(models.Consent, client=client, subject=user):
        backend.delete(consent)


def test_max_age_expired(testclient, user, client, keypair, trusted_client, backend):
    max_age = int(datetime.timedelta(minutes=15).total_seconds())

    with time_machine.travel("2025-01-01 02:30:00+00:00", tick=False):
        res = testclient.get("/login")

        res.form["login"] = "user"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

    with time_machine.travel("2025-01-01 03:00:00+00:00", tick=False):
        res = testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type="code",
                client_id=client.client_id,
                scope="openid",
                nonce="somenonce",
                redirect_uri="https://client.test/redirect1",
                max_age=max_age,
            ),
        ).follow()

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

        res = res.form.submit(name="answer", value="accept", status=302)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]

    with time_machine.travel("2025-01-01 03:01:00+00:00", tick=False):
        res = testclient.post(
            "/oauth/token",
            params=dict(
                grant_type="authorization_code",
                code=code,
                scope="openid",
                redirect_uri=client.redirect_uris[0],
            ),
            headers={"Authorization": f"Basic {client_credentials(client)}"},
        )

    for consent in backend.query(models.Consent, client=client, subject=user):
        backend.delete(consent)
