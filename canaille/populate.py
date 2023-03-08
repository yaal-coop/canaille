import random

import faker
from canaille.i18n import available_language_codes
from canaille.models import Group
from canaille.models import User
from faker.config import AVAILABLE_LOCALES


def faker_generator():
    locales = list(set(available_language_codes()) & set(AVAILABLE_LOCALES))
    return faker.Faker(locales)


def fake_users(nb=1):
    fake = faker_generator()
    locale = random.choice(fake.locales)
    users = list()
    for _ in range(nb):
        profile = fake.profile()
        user = User(
            cn=profile["name"],
            givenName=profile["name"].split(" ")[0],
            sn=profile["name"].split(" ")[1],
            uid=profile["username"],
            mail=profile["mail"],
            telephoneNumber=profile["ssn"],
            labeledURI=profile["website"][0],
            postalAddress=profile["residence"],
            userPassword=fake.password(),
            preferredLanguage=locale,
        )
        user.save()
        users.append(user)
    return users


def fake_groups(nb=1, nb_users_max=1):
    fake = faker_generator()
    users = User.query()
    groups = list()
    for _ in range(nb):
        group = Group(
            cn=fake.unique.word(),
            description=fake.sentence(),
        )
        nb_users = random.randrange(1, nb_users_max + 1)
        group.member = list({random.choice(users) for _ in range(nb_users)})
        group.save()
        groups.append(group)
    return groups
