import pytest
from canaille.backends import BaseBackend


def test_required_methods(testclient):
    with pytest.raises(NotImplementedError):
        BaseBackend.install(config=None)

    with pytest.raises(NotImplementedError):
        BaseBackend.validate({})

    backend = BaseBackend(testclient.app.config)
    with pytest.raises(NotImplementedError):
        backend.setup()

    with pytest.raises(NotImplementedError):
        backend.teardown()

    with pytest.raises(NotImplementedError):
        backend.has_account_lockability()
