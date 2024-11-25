import pytest
from scim2_client.engines.werkzeug import TestSCIMClient
from scim2_tester import check_server

from canaille.scim.endpoints import bp


def test_scim_tester(app, backend):
    # currently the tester create empty groups because it cannot handle references
    # but LDAP does not support empty groups
    # https://github.com/python-scim/scim2-tester/issues/15

    if "ldap" in backend.__class__.__module__:
        pytest.skip()

    client = TestSCIMClient(app, scim_prefix=bp.url_prefix)
    check_server(client, raise_exceptions=True)
