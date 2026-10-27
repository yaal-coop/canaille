import datetime

from canaille.app import models


def test_delete_user_with_webauthn_credential(backend, user):
    """Deleting a user removes it from its WebAuthn credentials."""
    credential = models.WebAuthnCredential(
        credential_id=b"test_credential",
        public_key=b"test_public_key",
        sign_count=0,
        created_at=datetime.datetime.now(datetime.UTC),
        user=user,
    )
    backend.save(credential)

    backend.delete(user)
    backend.reload(credential)
    assert credential.user is None
    assert backend.query(models.WebAuthnCredential, user=user) == []

    backend.delete(credential)
    assert backend.get(models.WebAuthnCredential, id=credential.id) is None
