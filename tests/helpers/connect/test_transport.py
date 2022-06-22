import pytest

import pyunicore.helpers.connect.transport as transport
import pyunicore.helpers.connect.authentication as authentication


@pytest.mark.parametrize(
    ("auth", "expected"),
    [
        (
            authentication.UserAuthentication(
                user="test_user",
                password="test_password",
            ),
            ("dGVzdF91c2VyOnRlc3RfcGFzc3dvcmQ=", False),
        ),
        (
            authentication.TokenAuthentication(token="test-token"),
            ("test-token", True),
        ),
    ],
)
def test_create_token(auth, expected):
    result = transport._create_token(auth)

    assert result == expected
