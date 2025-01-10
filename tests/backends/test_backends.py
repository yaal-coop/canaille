import pytest

from canaille.backends import Backend


def test_required_methods(testclient):
    with pytest.raises(NotImplementedError):
        Backend.install(app=None)

    with pytest.raises(NotImplementedError):
        Backend.validate({})

    backend = Backend(testclient.app.config["CANAILLE"])

    with pytest.raises(NotImplementedError):
        backend.has_account_lockability()
