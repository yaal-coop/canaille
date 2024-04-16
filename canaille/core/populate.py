import random

import faker
from faker.config import AVAILABLE_LOCALES

from canaille.app import models
from canaille.app.i18n import available_language_codes
from canaille.backends import Backend


def fake_users(nb=1):
    locales = list(set(available_language_codes()) & set(AVAILABLE_LOCALES))
    faker_obj = faker.Faker(locales)
    users = list()

    # TODO The day faker supports unique profiles,
    # we should use them so the different user values would be coherent
    # https://github.com/joke2k/faker/issues/1817
    for _ in range(nb):
        try:
            locale = random.choice(locales)
            fake = faker_obj[locale]
            name = fake.unique.name()
            user = models.User(
                formatted_name=name,
                given_name=name.split(" ")[0],
                family_name=name.split(" ")[1],
                user_name=fake.unique.user_name(),
                emails=[fake.unique.email()],
                phone_numbers=[fake.unique.ssn()],
                profile_url=fake.unique.uri(),
                formatted_address=fake.unique.address(),
                street=fake.street_name(),
                postal_code=fake.postcode(),
                locality=fake.city(),
                region=fake.state(),
                employee_number=str(fake.unique.random_number()),
                department=fake.word(),
                title=fake.job(),
                password=fake.password(),
                preferred_language=fake._locales[0],
            )
            Backend.instance.save(user)
            users.append(user)
        except Exception:  # pragma: no cover
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
            nb_users = random.randrange(1, nb_users_max + 1)
            group.members = list({random.choice(users) for _ in range(nb_users)})
            Backend.instance.save(group)
            groups.append(group)
        except Exception:  # pragma: no cover
            pass
    return groups
