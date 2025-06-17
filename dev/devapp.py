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
        app.backend.install(app)
        with app.backend.session():
            if app.backend.query(models.User):
                return

            jane = models.User(
                formatted_name="Jane Doe",
                given_name="Jane",
                family_name="Doe",
                user_name="admin",
                display_name="Jane.D",
                emails=["admin@example.org"],
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
            )
            app.backend.save(jane)

            jack = models.User(
                formatted_name="Jack Doe",
                given_name="Jack",
                family_name="Doe",
                user_name="moderator",
                display_name="👮 Jack 👮",
                emails=["moderator@example.org"],
                password="moderator",
                phone_numbers=["555-000-002"],
                profile_url="https://moderator.example",
                employee_number="1002",
                department="west",
            )
            app.backend.save(jack)

            john = models.User(
                formatted_name="John Doe",
                given_name="John",
                family_name="Doe",
                user_name="user",
                display_name="Johnny",
                emails=["user@example.org"],
                password="user",
                phone_numbers=["555-000-001"],
                profile_url="https://user.example",
                employee_number="1001",
                department="west",
            )
            app.backend.save(john)

            james = models.User(
                formatted_name="James Doe",
                given_name="James",
                family_name="Doe",
                user_name="james",
                emails=["james@example.org"],
            )
            app.backend.save(james)

            users = models.Group(
                display_name="users",
                members=[jane, jack, john, james],
                description="The regular users.",
            )
            app.backend.save(users)

            admins = models.Group(
                display_name="admin",
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
                client_id="client1",
                client_secret="2xYPSReTQRmGG1yppMVZQ0ASXwFejPyirvuPbKhNa6TmKC5x",
                client_name="Client1",
                contacts=["admin@example.org"],
                client_uri="http://client1.localhost:5001",
                redirect_uris=[
                    "http://localhost:5001/login_callback",
                    "http://localhost:5001/register_callback",
                    "http://client1.localhost:5001/login_callback",
                    "http://client1.localhost:5001/register_callback",
                ],
                post_logout_redirect_uris=[
                    "http://localhost:5001/logout_callback",
                    "http://client1.localhost:5001/logout_callback",
                ],
                tos_uri="http://client1.localhost:5001/tos",
                policy_uri="http://client1.localhost:5001/policy",
                grant_types=[
                    "authorization_code",
                    "refresh_token",
                    "client_credentials",
                    "urn:ietf:params:oauth:grant-type:jwt-bearer",
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
                client_id="client2",
                client_secret="ouFJE5WpICt6hxTyf8icXPeeklMektMY4gV0Rmf3aY60VElA",
                client_name="Client2",
                contacts=["admin@example.org"],
                client_uri="http://client2.localhost:5002",
                redirect_uris=[
                    "http://localhost:5002/login_callback",
                    "http://client2.localhost:5002/login_callback",
                ],
                post_logout_redirect_uris=[
                    "http://localhost:5002/logout_callback",
                    "http://localhost:5002/register_callback",
                    "http://client2.localhost:5002/logout_callback",
                    "http://client2.localhost:5002/register_callback",
                ],
                tos_uri="http://client2.localhost:5002/tos",
                policy_uri="http://client2.localhost:5002/policy",
                grant_types=[
                    "authorization_code",
                    "refresh_token",
                    "client_credentials",
                    "urn:ietf:params:oauth:grant-type:jwt-bearer",
                ],
                scope=["openid", "profile", "email", "groups", "address", "phone"],
                response_types=["code", "id_token"],
                token_endpoint_auth_method="client_secret_basic",
                trusted=True,
            )
            app.backend.save(client2)
            client2.audience = [client2]
            app.backend.save(client2)

            token = models.Token(
                token_id="EZWsi6omQRbJjWeq7rk8vcBVYz4PNbBXov97Z1D4mqxZgyQv",
                access_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwOi8vbG9jYWxob3N0OjUwMDAvIiwiYXVkIjpbIjFKR2trekNiZUhwR3RscWdJNUVFTkJ5ZiJdLCJpYXQiOjE3MzYxNjQwODIsImV4cCI6MTczNzAyODA4MiwiYXV0aF90aW1lIjoxNzM2MTY0MDgyLCJuYW1lIjoiSmFuZSBEb2UiLCJncm91cHMiOlsiaW1wb3J0YW50IiwiYWRtaW5zIiwidXNlcnMiXSwic3ViIjoiYWRtaW4iLCJnaXZlbl9uYW1lIjoiSmFuZSIsImVtYWlsIjoiYWRtaW5AbXlkb21haW4udGxkIiwicGhvbmVfbnVtYmVyIjoiNTU1LTAwMC0wMDAiLCJmYW1pbHlfbmFtZSI6IkRvZSIsIndlYnNpdGUiOiJodHRwczovL2FkbWluLmV4YW1wbGUiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJKYW5lLkQiLCJhZGRyZXNzIjoiMTIzLCBBZG1pbiBMYW5lIC0gR290aGFtIENpdHkgMTIzNDUifQ.gUy9wahjIy4PGGaI_8nIIeXyFdL2ngRLA43uuvlSLXq25bLfi9gsXNGuuuvwya0Qd6zjXJ4S9_q_Kr9oSgWAUQ1J-_F7-59_LSr2YYWYh05gWaRvKG7TqHHX7PIbx3Iv_ire_73xkLVQOG8KhLcP3DHfpBecwJbdFzk30CWDbCVFtWK8DdsffAaFGb2pnK-FdodmEQOBM0i58phbQcGdhJdCSMjJUy0y3KzSt9WqbkGA0avqzAXhiHCOn5A1rveqV0oBgFIODwcqA59XLcXTAD40DKFWQMm4AhH33R4Y4IHr3rupv2h06UTg_UvHw12xdwJgzKrPfZmAxUB8ZQKRBw",
                client=client1,
                subject=john,
                type="Bearer",
                refresh_token="aCm97aw3gFlPBpV6EpUq8WnN0LVm4mFwAxkOMkVhAEjqu2tZ",
                scope=[
                    "openid",
                    "profile",
                    "email",
                    "groups",
                    "address",
                    "phone",
                ],
                issue_date=datetime.datetime.now(tz=datetime.timezone.utc),
                lifetime=60 * 60 * 24,
                audience=[client1],
            )
            app.backend.save(token)

            fake_users(50)
            fake_groups(10, nb_users_max=10)


def create_app(config=None):
    app = canaille_app(config=config)
    try:
        populate(app)
    except:
        app.logger.exception("Something happen during the app initialization")

    return app
