import base64


def client_credentials(client):
    return base64.b64encode(
        client.client_id.encode("utf-8") + b":" + client.client_secret.encode("utf-8")
    ).decode("utf-8")
