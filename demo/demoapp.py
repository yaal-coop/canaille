import os
import sys


if os.path.exists("../canaille"):
    sys.path.append("../canaille")


from canaille import create_app as canaille_app


def create_app():
    app = canaille_app()

    @app.before_first_request
    def populate():
        from canaille.backends.ldap.backend import setup_backend
        from canaille.backends.ldap.backend import teardown_backend
        from canaille.core.models import Group
        from canaille.core.models import User
        from canaille.oidc.models import Client

        setup_backend(app)
        jane = User(
            formatted_name="Jane Doe",
            given_name="Jane",
            family_name="Doe",
            user_name="admin",
            display_name="Jane.D",
            email="admin@mydomain.tld",
            password="admin",
            phone_number="555-000-000",
            profile_url="https://admin.example",
            formatted_address="123, Admin Lane - Gotham City 12345",
            street="Admin Lane",
            postal_code="12345",
            city="Gotham City",
            region="North Pole",
            employee_number="1000",
            department_number="east",
        )
        jane.save()

        jack = User(
            formatted_name="Jack Doe",
            given_name="Jack",
            family_name="Doe",
            user_name="moderator",
            display_name="👮 Jack 👮",
            email="moderator@mydomain.tld",
            password="moderator",
            phone_number="555-000-002",
            profile_url="https://moderator.example",
            employee_number="1002",
            department_number="west",
        )
        jack.save()

        john = User(
            formatted_name="John Doe",
            given_name="John",
            family_name="Doe",
            user_name="user",
            display_name="Johnny",
            email="user@mydomain.tld",
            password="user",
            phone_number="555-000-001",
            profile_url="https://user.example",
            employee_number="1001",
            department_number="west",
        )
        john.save()

        james = User(
            formatted_name="James Doe",
            given_name="James",
            family_name="Doe",
            user_name="james",
            email="james@mydomain.tld",
        )
        james.save()

        users = Group(
            display_name="users",
            members=[jane, jack, john, james],
            description="The regular users.",
        )
        users.save()

        users = Group(
            display_name="admins",
            members=[jane],
            description="The administrators.",
        )
        users.save()

        users = Group(
            display_name="moderators",
            members=[james],
            description="People who can manage users.",
        )
        users.save()

        client1 = Client(
            client_id="1JGkkzCbeHpGtlqgI5EENByf",
            client_secret="2xYPSReTQRmGG1yppMVZQ0ASXwFejPyirvuPbKhNa6TmKC5x",
            client_name="Client1",
            contacts=["admin@mydomain.tld"],
            client_uri="http://localhost:5001",
            redirect_uris=["http://localhost:5001/authorize"],
            post_logout_redirect_uris=["http://localhost:5001/"],
            tos_uri="http://localhost:5001/tos",
            policy_uri="http://localhost:5001/policy",
            grant_types=["authorization_code", "refresh_token"],
            scope=["openid", "profile", "email", "groups", "address", "phone"],
            response_types=["code", "id_token"],
            token_endpoint_auth_method="client_secret_basic",
        )
        client1.save()

        client2 = Client(
            client_id="gn4yFN7GDykL7QP8v8gS9YfV",
            client_secret="ouFJE5WpICt6hxTyf8icXPeeklMektMY4gV0Rmf3aY60VElA",
            client_name="Client2",
            contacts=["admin@mydomain.tld"],
            client_uri="http://localhost:5002",
            redirects_uris=["http://localhost:5002/authorize"],
            post_logout_redirect_uris=["http://localhost:5002/"],
            tos_uri="http://localhost:5002/tos",
            policy_uri="http://localhost:5002/policy",
            grant_types=["authorization_code", "refresh_token"],
            scope=["openid", "profile", "email", "groups", "address", "phone"],
            response_types=["code", "id_token"],
            token_endpoint_auth_method="client_secret_basic",
            preconsent=True,
        )
        client2.save()

        teardown_backend(app)

    return app
