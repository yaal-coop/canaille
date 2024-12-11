from scim2_tester import Status
from scim2_tester import check_server


def test_scim_tester(scim_client):
    results = check_server(scim_client, raise_exceptions=True)
    assert all(result.status == Status.SUCCESS for result in results)
