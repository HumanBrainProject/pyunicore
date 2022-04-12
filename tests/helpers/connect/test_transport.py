import pyunicore.helpers.connect.transport as transport


def test_create_token():
    user = "test_user"
    password = "test_password"
    expected = "dGVzdF91c2VyOnRlc3RfcGFzc3dvcmQ="

    result = transport._create_token(user=user, password=password)

    assert result == expected
