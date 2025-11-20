import random

import faker
from faker.config import AVAILABLE_LOCALES
from flask import current_app

from canaille.app import models
from canaille.app.i18n import available_language_codes
from canaille.backends import Backend

try:
    import python_avatars as pa

    HAS_PYTHON_AVATARS = True
except ImportError:  # pragma: no cover
    HAS_PYTHON_AVATARS = False


def generate_avatar():
    """Generate a random avatar as SVG bytes.

    Returns None for LDAP backend as it expects JPEG (jpegPhoto attribute).
    """
    if not HAS_PYTHON_AVATARS:  # pragma: no cover
        return None

    # LDAP backend expects JPEG in jpegPhoto attribute, not SVG
    try:
        if (
            Backend.instance and Backend.instance.__class__.__name__ == "LDAPBackend"
        ):  # pragma: no cover
            return None
    except (AttributeError, RuntimeError):  # pragma: no cover
        # Backend.instance not yet initialized, skip LDAP check
        pass

    avatar = pa.Avatar.random()
    svg_bytes = avatar.render().encode("utf-8")
    return svg_bytes


def fake_users(nb=1):
    locales = list(set(available_language_codes()) & set(AVAILABLE_LOCALES))
    faker_obj = faker.Faker(locales).unique
    users = list()

    for _ in range(nb):
        try:
            locale = random.choice(locales)
            fake = faker_obj[locale]
            profile = fake.profile()
            name = profile["name"]
            user = models.User(
                formatted_name=name,
                given_name=name.split(" ")[0],
                family_name=name.split(" ")[1],
                user_name=profile["username"],
                emails=[profile["mail"]],
                phone_numbers=[profile["ssn"]],
                profile_url=profile["website"][0],
                formatted_address=profile["address"],
                street=fake.street_name(),
                postal_code=fake.postcode(),
                locality=fake.city(),
                region=fake.state(),
                employee_number=str(fake.random_number()),
                department=fake.word(),
                title=profile["job"],
                password=fake.password(),
                preferred_language=locale,
                photo=generate_avatar(),
            )
            Backend.instance.save(user)
            users.append(user)
        except Exception:  # pragma: no cover
            current_app.logger.debug("Failed to create fake user", exc_info=True)
            pass
    return users


def fake_groups(nb=1, nb_users_max=1):
    users = Backend.instance.query(models.User)
    groups = list()
    fake = faker.Faker(["en_US"])
    for _ in range(nb):
        try:
            group = models.Group(
                display_name=fake.unique.word(),
                description=fake.sentence(),
            )
            if nb_users_max:
                nb_users = random.randrange(1, nb_users_max + 1)
                group.members = list({random.choice(users) for _ in range(nb_users)})
            Backend.instance.save(group)
            groups.append(group)
        except Exception:  # pragma: no cover
            current_app.logger.debug("Failed to create fake groups", exc_info=True)
            pass
    return groups
