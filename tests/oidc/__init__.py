import base64


def client_credentials(client):
    return base64.b64encode(
        client.oauthClientID.encode("utf-8")
        + b":"
        + client.oauthClientSecret.encode("utf-8")
    ).decode("utf-8")
