from dataclasses import dataclass
from typing import Any

from flask import current_app
from flask import url_for
from scim2_models import NotFoundException
from scim2_models import PreconditionFailedException
from scim2_models import Resource
from scim2_models import ResourceType
from scim2_models import SearchRequest
from scim2_models import UniquenessException
from scim2_server.storage import ScimStorage

from canaille.app import models
from canaille.backends import Backend

from .casting import group_from_canaille_to_scim_server
from .casting import group_from_scim_to_canaille
from .casting import make_etag
from .casting import self_edition
from .casting import user_from_canaille_to_scim_server
from .casting import user_from_scim_to_canaille


def resource_url(endpoint, resource_id):
    """Return the SCIM URL of a resource."""
    return url_for("scim.scim", path=f"{endpoint}/{resource_id}", _external=True)


def user_to_scim(user):
    scim_user = user_from_canaille_to_scim_server(user)
    for group in scim_user.groups or []:
        group.ref = resource_url("Groups", group.value)
    return scim_user


def group_to_scim(group):
    scim_group = group_from_canaille_to_scim_server(group)
    for member in scim_group.members or []:
        member.ref = resource_url("Users", member.value)
    return scim_group


@dataclass
class Kind:
    """How a SCIM resource type maps to a Canaille model."""

    model_name: str
    unique_attribute: str
    to_scim: Any
    from_scim: Any

    @property
    def model(self):
        return getattr(models, self.model_name)


KINDS = {
    "User": Kind("User", "user_name", user_to_scim, user_from_scim_to_canaille),
    "Group": Kind("Group", "display_name", group_to_scim, group_from_scim_to_canaille),
}


class CanailleStorage(ScimStorage):
    """Store the SCIM resources in the Canaille backend.

    A storage serves the requests of one token. A user can only modify
    the attributes of their ``WRITE`` ACL on their own account.
    """

    def __init__(self, token):
        self.token = token

    def get(self, resource_type: ResourceType, resource_id: str) -> Resource[Any]:
        kind = KINDS[resource_type.id]
        return kind.to_scim(self._load(kind, resource_id))

    def search(
        self, resource_types: list[ResourceType], search_request: SearchRequest[Any]
    ) -> tuple[int, list[Resource[Any]]]:
        start = search_request.start_index_0 or 0
        stop = None if search_request.count is None else start + search_request.count
        if search_request.filter is not None or search_request.sort_by is not None:
            kinds = [KINDS[resource_type.id] for resource_type in resource_types]
            resources = [
                kind.to_scim(instance)
                for kind in kinds
                for instance in Backend.instance.query(kind.model)
            ]
            found = [
                resource
                for resource in resources
                if search_request.filter is None
                or search_request.filter.match(resource)
            ]
            return len(found), search_request.sort(found)[start:stop]

        total = 0
        resources = []
        for resource_type in resource_types:
            kind = KINDS[resource_type.id]
            first = max(start - total, 0)
            last = None if stop is None else max(stop - total, 0)
            if last is None or last > first:
                instances = Backend.instance.query(kind.model)[first:last]
                resources += [kind.to_scim(instance) for instance in instances]
            total += Backend.instance.count(kind.model)
        return total, resources

    def create(
        self, resource_type: ResourceType, resource: Resource[Any]
    ) -> Resource[Any]:
        kind = KINDS[resource_type.id]
        self._check_uniqueness(kind, resource)
        instance = kind.from_scim(resource, kind.model())
        Backend.instance.save(instance)
        self._log("created", instance)
        return kind.to_scim(instance)

    def update(
        self,
        resource_type: ResourceType,
        resource: Resource[Any],
        *,
        expected_version: str | None = None,
    ) -> Resource[Any]:
        kind = KINDS[resource_type.id]
        instance = self._load(kind, resource.id)
        self._check_version(instance, expected_version)
        self._check_uniqueness(kind, resource)
        from_scim = kind.from_scim
        if self._is_subject(instance):
            from_scim = self_edition(from_scim)
        from_scim(resource, instance)
        Backend.instance.save(instance)
        self._log("updated", instance)
        return kind.to_scim(instance)

    def delete(
        self,
        resource_type: ResourceType,
        resource_id: str,
        *,
        expected_version: str | None = None,
    ) -> None:
        kind = KINDS[resource_type.id]
        instance = self._load(kind, resource_id)
        self._check_version(instance, expected_version)
        self._log("deleted", instance)
        Backend.instance.delete(instance)

    @staticmethod
    def _load(kind, resource_id):
        instance = Backend.instance.get(kind.model, id=resource_id)
        if not instance:
            raise NotFoundException(detail=f"Resource {resource_id} not found")
        return instance

    @staticmethod
    def _check_version(instance, expected_version):
        if expected_version is not None and make_etag(instance) != expected_version:
            raise PreconditionFailedException(detail="The resource version changed")

    @staticmethod
    def _check_uniqueness(kind, resource):
        """Check the unique value before the instance changes, as SQL would flush it."""
        value = getattr(resource, kind.unique_attribute)
        candidates = Backend.instance.fuzzy(
            kind.model, value, attributes=[kind.unique_attribute]
        )
        if any(
            candidate.id != resource.id
            and getattr(candidate, kind.unique_attribute).lower() == value.lower()
            for candidate in candidates
        ):
            raise UniquenessException(detail=f"{value} is already taken")

    def _is_subject(self, instance):
        subject = self.token.subject
        return (
            isinstance(instance, models.User) and subject and subject.id == instance.id
        )

    def _log(self, action, instance):
        current_app.logger.security(
            f"SCIM {action} {type(instance).__name__.lower()} {instance.id} "
            f"by client {self.token.client.client_id}"
        )
