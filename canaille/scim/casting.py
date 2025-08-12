import datetime

from flask import url_for
from scim2_models import Meta

from canaille.app import models
from canaille.backends import Backend
from canaille.scim.models import EnterpriseUser
from canaille.scim.models import Group
from canaille.scim.models import User


def user_from_canaille_to_scim(user, user_class, enterprise_user_class):
    scim_user_class = user_class if user_class != User else User[EnterpriseUser]
    scim_user = scim_user_class(
        meta=Meta(
            resource_type="User",
            created=user.created,
            last_modified=user.last_modified,
            location=url_for("scim.query_user", user=user, _external=True),
        ),
        user_name=user.user_name,
        preferred_language=user.preferred_language,
        name=user_class.Name(
            formatted=user.formatted_name,
            family_name=user.family_name,
            given_name=user.given_name,
        )
        if (user.formatted_name or user.family_name or user.given_name)
        else None,
        display_name=user.display_name,
        title=user.title,
        profile_url=user.profile_url,
        emails=[
            user_class.Emails(
                value=email,
            )
            for email in user.emails or []
        ]
        or None,
        phone_numbers=[
            user_class.PhoneNumbers(
                value=phone_number,
            )
            for phone_number in user.phone_numbers or []
        ]
        or None,
        addresses=[
            user_class.Addresses(
                formatted=user.formatted_address,
                street_address=user.street,
                postal_code=user.postal_code,
                locality=user.locality,
                region=user.region,
            )
        ]
        if (
            user.formatted_address
            or user.street
            or user.postal_code
            or user.locality
            or user.region
        )
        else None,
        photos=[
            user_class.Photos(
                value=url_for(
                    "core.account.photo", user=user, field="photo", _external=True
                ),
                primary=True,
                type=user_class.Photos.Type.photo,
            )
        ]
        if user.photo
        else None,
        groups=[
            user_class.Groups(
                value=group.id,
                display=group.display_name,
                ref=url_for("scim.query_group", group=group, _external=True),
            )
            for group in user.groups or []
        ]
        or None,
        active=user.lock_date is None,
    )
    if enterprise_user_class:
        scim_user[enterprise_user_class] = enterprise_user_class(
            employee_number=user.employee_number,
            organization=user.organization,
            department=user.department,
        )
    return scim_user


def user_from_canaille_to_scim_server(user):
    scim_user = user_from_canaille_to_scim(user, User, EnterpriseUser)
    scim_user.id = user.id
    return scim_user


def user_from_scim_to_canaille(scim_user: User, user):
    user.user_name = scim_user.user_name
    user.password = scim_user.password
    user.preferred_language = scim_user.preferred_language
    user.formatted_name = scim_user.name.formatted if scim_user.name else None
    user.family_name = scim_user.name.family_name if scim_user.name else None
    user.given_name = scim_user.name.given_name if scim_user.name else None
    user.display_name = scim_user.display_name
    user.title = scim_user.title
    user.profile_url = scim_user.profile_url
    user.emails = [email.value for email in scim_user.emails or []] or None
    user.phone_numbers = [
        phone.value for phone in scim_user.phone_numbers or []
    ] or None

    if scim_user.addresses:
        address = scim_user.addresses[0]
        user.formatted_address = address.formatted
        user.street = address.street_address
        user.postal_code = address.postal_code
        user.locality = address.locality
        user.region = address.region
    else:
        user.formatted_address = None
        user.street = None
        user.postal_code = None
        user.locality = None
        user.region = None
    # TODO: delete the photo
    # if scim_user.photos and scim_user.photos[0].value:
    #    user.photo = scim_user.photos[0].value
    user.employee_number = (
        scim_user[EnterpriseUser].employee_number if scim_user[EnterpriseUser] else None
    )
    user.organization = (
        scim_user[EnterpriseUser].organization if scim_user[EnterpriseUser] else None
    )
    user.department = (
        scim_user[EnterpriseUser].department if scim_user[EnterpriseUser] else None
    )
    user.groups = [
        Backend.instance.get(models.Group, group.value)
        for group in scim_user.groups or []
        if group.value
    ]
    if not scim_user.active:
        user.lock_date = datetime.datetime.now(datetime.timezone.utc)
    else:
        user.lock_date = None
    return user


def group_from_canaille_to_scim(group, group_class):
    return group_class(
        meta=Meta(
            resource_type="Group",
            created=group.created,
            last_modified=group.last_modified,
            location=url_for("scim.query_group", group=group, _external=True),
        ),
        display_name=group.display_name,
    )


def group_from_canaille_to_scim_server(group):
    scim_group = group_from_canaille_to_scim(group, Group)
    scim_group.id = group.id

    scim_group.members = [
        Group.Members(
            value=user.identifier,
            display=user.display_name,
            ref=url_for("scim.query_user", user=user, _external=True),
        )
        for user in group.members or []
    ] or None
    return scim_group


def group_from_scim_to_canaille(scim_group: Group, group):
    group.display_name = scim_group.display_name

    members = []
    for member in scim_group.members or []:
        if user := Backend.instance.get(models.User, member.value):
            members.append(user)

    group.members = members

    return group
