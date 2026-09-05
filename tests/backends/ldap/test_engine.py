from unittest import mock

from ldap.controls.ppolicy import PasswordPolicyError

from canaille.backends.ldap.engine import PasswordStatus


def test_check_password_ignores_unrelated_controls(backend):
    """Only password policy controls are interpreted.

    A control of another type carrying the same error value than a locked
    account must not lock the authentication down.
    """
    other_control = mock.Mock(
        controlType="1.2.3.4",
        error=PasswordPolicyError.namedValues["accountLocked"],
    )

    with mock.patch("ldap.initialize") as initialize:
        initialize.return_value.simple_bind_s.return_value = (
            None,
            None,
            None,
            [other_control],
        )
        status = backend.engine.check_password("cn=foo,dc=example,dc=org", "password")

    assert status == PasswordStatus.SUCCESS
