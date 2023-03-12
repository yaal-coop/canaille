import random

import faker
import ldap
from canaille.i18n import available_language_codes
from canaille.models import Group
from canaille.models import User
from faker.config import AVAILABLE_LOCALES


def faker_generator(locales=None):
    locales = locales or list(set(available_language_codes()) & set(AVAILABLE_LOCALES))
    return [faker.Faker(locale) for locale in locales]


def fake_users(nb=1):
    fakes = faker_generator()
    users = list()
    for _ in range(nb):
        try:
            fake = random.choice(fakes)
            name = fake.unique.name()
            user = User(
                cn=name,
                givenName=name.split(" ")[0],
                sn=name.split(" ")[1],
                uid=fake.unique.user_name(),
                mail=fake.unique.email(),
                telephoneNumber=fake.unique.ssn(),
                labeledURI=fake.unique.uri(),
                postalAddress=fake.unique.address(),
                street=fake.street_name(),
                postalCode=fake.postcode(),
                l=fake.city(),
                st=fake.state(),
                employeeNumber=str(fake.unique.random_number()),
                departmentNumber=fake.word(),
                title=fake.job(),
                userPassword=fake.password(),
                preferredLanguage=fake._locales[0],
            )
            user.save()
            users.append(user)
        except ldap.ALREADY_EXISTS:  # pragma: no cover
            pass
    return users


def fake_groups(nb=1, nb_users_max=1):
    fake = faker_generator(["en_US"])[0]
    users = User.query()
    groups = list()
    for _ in range(nb):
        try:
            group = Group(
                cn=fake.unique.word(),
                description=fake.sentence(),
            )
            nb_users = random.randrange(1, nb_users_max + 1)
            group.member = list({random.choice(users) for _ in range(nb_users)})
            group.save()
            groups.append(group)
        except ldap.ALREADY_EXISTS:  # pragma: no cover
            pass
    return groups
