import pytest
from scim2_tester import check_server


def test_scim_tester(scim_client, backend):
    # currently the tester create empty groups because it cannot handle references
    # but LDAP does not support empty groups
    # https://github.com/python-scim/scim2-tester/issues/15

    if "ldap" in backend.__class__.__module__:
        pytest.skip()

    check_server(scim_client, raise_exceptions=True)
