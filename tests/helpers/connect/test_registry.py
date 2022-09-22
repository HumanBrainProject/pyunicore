import functools
from typing import Dict

import pytest

import pyunicore.client
import pyunicore.testing as testing
import pyunicore.helpers.connect.registry as _registry
import pyunicore.helpers.connect.site as _site
import pyunicore.credentials as credentials


@pytest.fixture()
def transport():
    return testing.FakeTransport()


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
        credentials=creds,
    )

    assert isinstance(result, pyunicore.client.Registry)


@pytest.mark.parametrize(
    ("login_successful", "expected"),
    [
        (False, _site.AuthenticationFailedException()),
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
            credentials=creds,
        )

        assert isinstance(result, expected)


@pytest.mark.parametrize(
    ("site", "expected"),
    [
        ("test_site", "test_api_url"),
        ("test_unavailable_site", ValueError()),
    ],
)
def test_get_site_api_url_from_registry(monkeypatch, transport, site, expected):
    monkeypatch.setattr(
        pyunicore.client,
        "Registry",
        create_fake_registry(contains={"test_site": "test_api_url"}),
    )

    with testing.expect_raise_if_exception(expected):
        result = _registry._get_site_api_url(
            site=site,
            transport=transport,
            registry_url="test_registry_url",
        )

        assert result == expected
