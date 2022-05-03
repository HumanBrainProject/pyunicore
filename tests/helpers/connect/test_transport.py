import pytest

import pyunicore.helpers.connect.transport as transport
import pyunicore.helpers.connect.authorization as authorization


@pytest.mark.parametrize(
    ("auth", "expected"),
    [
        (
            authorization.UserAuthorization(
                user="test_user",
                password="test_password",
            ),
            ("dGVzdF91c2VyOnRlc3RfcGFzc3dvcmQ=", False),
        ),
        (
            authorization.TokenAuthorization(token="test-token"),
            ("test-token", True),
        ),
    ],
)
def test_create_token(auth, expected):
    result = transport._create_token(auth)

    assert result == expected
