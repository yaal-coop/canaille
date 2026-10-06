from canaille.app import models


def test_token_lookup_is_case_sensitive(backend, token):
    """A token cannot be found with a different case."""
    assert backend.get(models.Token, access_token=token.access_token.swapcase()) is None
    assert (
        backend.get(models.Token, refresh_token=token.refresh_token.swapcase()) is None
    )


def test_authorization_code_lookup_is_case_sensitive(backend, authorization):
    """An authorization code cannot be found with a different case."""
    assert backend.get(models.AuthorizationCode, code="MY-CODE") is None
