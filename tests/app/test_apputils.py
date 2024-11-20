from canaille.app import validate_uri


def test_validate_uri():
    assert validate_uri("https://canaille.test")
    assert validate_uri("scheme.with.dots://canaille.test")
    assert validate_uri("scheme.with.dots://localhost")
    assert validate_uri("scheme.with.dots://oauth")
    assert not validate_uri("invalid")
