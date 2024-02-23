import functools
from typing import Dict

import pytest

import pyunicore.client
import pyunicore.credentials as credentials
import pyunicore.helpers.connection.registry as _registry
import pyunicore.testing as testing


@pytest.fixture()
def credential():
    return credentials.UsernamePassword(username="test_user", password="test_password")


def create_fake_registry(contains: Dict[str, str]) -> functools.partial:
    return functools.partial(
        testing.FakeRegistry,
        contains=contains,
    )


def create_fake_client(login_successful: bool) -> functools.partial:
    return functools.partial(
        testing.FakeClient,
        login_successful=login_successful,
    )


def test_connect_to_registry(monkeypatch):
    monkeypatch.setattr(pyunicore.client, "Transport", testing.FakeTransport)

    registry_url = "test_registry_url"
    creds = credentials.UsernamePassword(
        username="test_user",
        password="test_password",
    )

    result = _registry.connect_to_registry(
        registry_url=registry_url,
        credential=creds,
    )

    assert isinstance(result, pyunicore.client.Registry)


@pytest.mark.parametrize(
    ("login_successful", "expected"),
    [
        (False, credentials.AuthenticationFailedException()),
        (True, testing.FakeClient),
    ],
)
def test_connect_to_site_from_registry(monkeypatch, login_successful, expected):
    monkeypatch.setattr(pyunicore.client, "Transport", testing.FakeTransport)
    monkeypatch.setattr(
        pyunicore.client,
        "Registry",
        create_fake_registry(contains={"test_site": "test_api_url"}),
    )
    monkeypatch.setattr(
        pyunicore.client,
        "Client",
        create_fake_client(login_successful=login_successful),
    )

    registry_url = "test_registry_url"
    site = "test_site"
    creds = credentials.UsernamePassword(
        username="test_user",
        password="test_password",
    )

    with testing.expect_raise_if_exception(expected):
        result = _registry.connect_to_site_from_registry(
            registry_url=registry_url,
            site_name=site,
            credential=creds,
        )

        assert isinstance(result, expected)


@pytest.mark.parametrize(
    ("site", "expected"),
    [
        ("test_site", "test_api_url"),
        ("test_unavailable_site", ValueError()),
    ],
)
def test_get_site_api_url_from_registry(monkeypatch, credential, site, expected):
    monkeypatch.setattr(
        pyunicore.client,
        "Registry",
        create_fake_registry(contains={"test_site": "test_api_url"}),
    )

    with testing.expect_raise_if_exception(expected):
        result = _registry._get_site_api_url(
            site=site,
            credential=credential,
            registry_url="test_registry_url",
        )

        assert result == expected
