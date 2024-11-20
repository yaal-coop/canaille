def test_issuer(testclient, user):
    res = testclient.get(
        "/.well-known/webfinger?resource=acct%3Auser%40mydomain.test&rel=http%3A%2F%2Fopenid.net%2Fspecs%2Fconnect%2F1.0%2Fissuer"
    )
    assert res.json == {
        "subject": "acct:user@mydomain.test",
        "links": [
            {
                "rel": "http://openid.net/specs/connect/1.0/issuer",
                "href": "https://auth.mydomain.test",
            }
        ],
    }


def test_resource_unknown(testclient):
    res = testclient.get(
        "/.well-known/webfinger?resource=acct%3Ainvalid%40mydomain.test&rel=http%3A%2F%2Fopenid.net%2Fspecs%2Fconnect%2F1.0%2Fissuer",
    )
    assert res.json == {
        "subject": "acct:invalid@mydomain.test",
        "links": [
            {
                "rel": "http://openid.net/specs/connect/1.0/issuer",
                "href": "https://auth.mydomain.test",
            }
        ],
    }


def test_bad_request(testclient, user):
    testclient.get("/.well-known/webfinger", status=400)
