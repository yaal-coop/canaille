import random

import faker
from faker.config import AVAILABLE_LOCALES

from canaille.app import models
from canaille.app.i18n import available_language_codes


def faker_generator(locales=None):
    locales = locales or list(set(available_language_codes()) & set(AVAILABLE_LOCALES))
    return faker.Faker(locales)


def fake_users(nb=1):
    users = list()
    for _ in range(nb):
        try:
            fake = faker_generator()
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
            user.save()
            users.append(user)
        except Exception:  # pragma: no cover
            pass
    return users


def fake_groups(nb=1, nb_users_max=1):
    users = models.User.query()
    groups = list()
    fake = faker_generator(["en_US"])
    for _ in range(nb):
        try:
            group = models.Group(
                display_name=fake.unique.word(),
                description=fake.sentence(),
            )
            nb_users = random.randrange(1, nb_users_max + 1)
            group.members = list({random.choice(users) for _ in range(nb_users)})
            group.save()
            groups.append(group)
        except Exception:  # pragma: no cover
            pass
    return groups
