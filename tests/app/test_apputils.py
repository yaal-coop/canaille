from canaille.app import validate_uri


def test_validate_uri():
    assert validate_uri("https://canaille.test")
    assert validate_uri("http://canaille.test")
    assert not validate_uri("data://canaille.test")
    assert not validate_uri("file://canaille.test")
    assert not validate_uri("javascript:alert()")
    assert not validate_uri("invalid")
    assert validate_uri("http://127.0.0.1")
    assert validate_uri("http://127.0.0.1:8000")
