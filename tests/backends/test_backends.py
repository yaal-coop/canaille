import pytest
from canaille.backends import Backend


def test_required_methods(testclient):
    with pytest.raises(NotImplementedError):
        Backend.install()

    with pytest.raises(NotImplementedError):
        Backend.validate({})

    backend = Backend(testclient.app.config)
    with pytest.raises(NotImplementedError):
        backend.setup()

    with pytest.raises(NotImplementedError):
        backend.teardown()
