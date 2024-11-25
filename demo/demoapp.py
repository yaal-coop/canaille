import datetime
import os
import sys

if os.path.exists("../canaille"):
    sys.path.append("../canaille")


from canaille import create_app as canaille_app


def populate(app):
    from canaille.app import models
    from canaille.core.populate import fake_groups
    from canaille.core.populate import fake_users

    with app.app_context():
        app.backend.install(app.config)
        with app.backend.session():
            if app.backend.query(models.User):
                return

            jane = models.User(
                formatted_name="Jane Doe",
                given_name="Jane",
                family_name="Doe",
                user_name="admin",
                display_name="Jane.D",
                emails=["admin@mydomain.tld"],
                password="admin",
                phone_numbers=["555-000-000"],
                profile_url="https://admin.example",
                formatted_address="123, Admin Lane - Gotham City 12345",
                street="Admin Lane",
                postal_code="12345",
                locality="Gotham City",
                region="North Pole",
                employee_number="1000",
                department="east",
                password_attribute="userPassword",
            )
            app.backend.save(jane)

            jack = models.User(
                formatted_name="Jack Doe",
                given_name="Jack",
                family_name="Doe",
                user_name="moderator",
                display_name="👮 Jack 👮",
                emails=["moderator@mydomain.tld"],
                password="moderator",
                phone_numbers=["555-000-002"],
                profile_url="https://moderator.example",
                employee_number="1002",
                department="west",
                password_attribute="userPassword",
            )
            app.backend.save(jack)

            john = models.User(
                formatted_name="John Doe",
                given_name="John",
                family_name="Doe",
                user_name="user",
                display_name="Johnny",
                emails=["user@mydomain.tld"],
                password="user",
                phone_numbers=["555-000-001"],
                profile_url="https://user.example",
                employee_number="1001",
                department="west",
                password_attribute="userPassword",
            )
            app.backend.save(john)

            james = models.User(
                formatted_name="James Doe",
                given_name="James",
                family_name="Doe",
                user_name="james",
                emails=["james@mydomain.tld"],
                password_attribute="userPassword",
            )
            app.backend.save(james)

            users = models.Group(
                display_name="users",
                members=[jane, jack, john, james],
                description="The regular users.",
            )
            app.backend.save(users)

            admins = models.Group(
                display_name="admins",
                members=[jane],
                description="The administrators.",
            )
            app.backend.save(admins)

            users = models.Group(
                display_name="moderators",
                members=[james],
                description="People who can manage users.",
            )
            app.backend.save(users)

            client1 = models.Client(
                client_id_issued_at=datetime.datetime.utcnow(),
                client_id="1JGkkzCbeHpGtlqgI5EENByf",
                client_secret="2xYPSReTQRmGG1yppMVZQ0ASXwFejPyirvuPbKhNa6TmKC5x",
                client_name="Client1",
                contacts=["admin@mydomain.tld"],
                client_uri="http://localhost:5001",
                redirect_uris=[
                    "http://localhost:5001/login_callback",
                    "http://localhost:5001/register_callback",
                ],
                post_logout_redirect_uris=["http://localhost:5001/logout_callback"],
                tos_uri="http://localhost:5001/tos",
                policy_uri="http://localhost:5001/policy",
                grant_types=[
                    "authorization_code",
                    "refresh_token",
                    "client_credentials",
                ],
                scope=["openid", "profile", "email", "groups", "address", "phone"],
                response_types=["code", "id_token"],
                token_endpoint_auth_method="client_secret_basic",
            )
            app.backend.save(client1)
            client1.audience = [client1]
            app.backend.save(client1)

            client2 = models.Client(
                client_id_issued_at=datetime.datetime.utcnow(),
                client_id="gn4yFN7GDykL7QP8v8gS9YfV",
                client_secret="ouFJE5WpICt6hxTyf8icXPeeklMektMY4gV0Rmf3aY60VElA",
                client_name="Client2",
                contacts=["admin@mydomain.tld"],
                client_uri="http://localhost:5002",
                redirect_uris=["http://localhost:5002/login_callback"],
                post_logout_redirect_uris=[
                    "http://localhost:5002/logout_callback",
                    "http://localhost:5002/register_callback",
                ],
                tos_uri="http://localhost:5002/tos",
                policy_uri="http://localhost:5002/policy",
                grant_types=[
                    "authorization_code",
                    "refresh_token",
                    "client_credentials",
                ],
                scope=["openid", "profile", "email", "groups", "address", "phone"],
                response_types=["code", "id_token"],
                token_endpoint_auth_method="client_secret_basic",
                preconsent=True,
            )
            app.backend.save(client2)
            client2.audience = [client2]
            app.backend.save(client2)

            fake_users(50)
            fake_groups(10, nb_users_max=10)


def create_app():
    app = canaille_app()
    try:
        populate(app)
    except:
        app.logger.exception("Something happen during the app initialization")

    return app
