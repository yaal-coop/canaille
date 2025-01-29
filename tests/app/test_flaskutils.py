from canaille.app.flask import set_parameter_in_url_query


def test_set_parameter_in_url_query():
    assert (
        set_parameter_in_url_query("https://auth.mydomain.test", foo="bar")
        == "https://auth.mydomain.test?foo=bar"
    )

    assert (
        set_parameter_in_url_query("https://auth.mydomain.test?foo=baz", foo="bar")
        == "https://auth.mydomain.test?foo=bar"
    )

    assert (
        set_parameter_in_url_query("https://auth.mydomain.test?foo=baz", hello="world")
        == "https://auth.mydomain.test?foo=baz&hello=world"
    )
