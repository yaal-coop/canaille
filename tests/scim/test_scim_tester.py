import pytest
from scim2_tester import Status
from scim2_tester import check_server
from scim2_tester.discovery import get_all_available_tags
from scim2_tester.discovery import get_standard_resource_types


@pytest.mark.parametrize("tag", get_all_available_tags())
@pytest.mark.parametrize("resource_type", [None] + get_standard_resource_types())
def test_individual_filters(scim_client, tag, resource_type):
    results = check_server(
        scim_client,
        raise_exceptions=True,
        include_tags={tag},
        resource_types=resource_type,
    )

    for result in results:
        assert result.status in (Status.SKIPPED, Status.SUCCESS)
