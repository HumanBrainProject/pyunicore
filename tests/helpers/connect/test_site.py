import functools

import pyunicore.testing as testing
import pyunicore.helpers.connect.site as _connect
import pytest
import pyunicore.client as pyunicore


@pytest.fixture()
def transport():
    return testing.FakeTransport()


def create_fake_client(login_successful: bool) -> functools.partial:
    return functools.partial(
        testing.FakeClient,
        login_successful=login_successful,
    )


@pytest.mark.parametrize(
    ("login_successful", "expected"),
    [
        (False, _connect.AuthenticationFailedException()),
        (True, testing.FakeClient),
    ],
)
def test_connect_to_site(monkeypatch, login_successful, expected):
    monkeypatch.setattr(pyunicore, "Transport", testing.FakeTransport)
    monkeypatch.setattr(
        pyunicore,
        "Client",
        create_fake_client(login_successful=login_successful),
    )

    api_url = "test-api-url"
    user = "test_user"
    password = "test_password"

    with testing.expect_raise_if_exception(expected):
        result = _connect.connect_to_site(
            site_api_url=api_url,
            user=user,
            password=password,
        )

        assert isinstance(result, expected)


@pytest.mark.parametrize(
    ("login", "expected"),
    [
        ({}, True),
        ({"test_login_info": "test_login"}, False),
    ],
)
def test_authentication_failed(login, expected):
    client = testing.FakeClient()
    client.add_login_info(login)

    result = _connect._authentication_failed(client)

    assert result == expected
