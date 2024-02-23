from typing import Dict

import pyunicore.client
from pyunicore import credentials
from pyunicore.helpers.connection import site as _site


def connect_to_registry(
    registry_url: str, credential: credentials.Credential
) -> pyunicore.client.Registry:
    """Connect to a registry.

    Args:
        registry_url (str): URL to the UNICORE registry.
        credential (pyunicore.credentials.Credential): Authentication method.

    Returns:
        pyunicore.client.Registry

    """
    return pyunicore.client.Registry(credential, url=registry_url)


def connect_to_site_from_registry(
    registry_url: str, site_name: str, credential: credentials.Credential
) -> pyunicore.client.Client:
    """Create a connection to a site's UNICORE API from the registry base URL.

    Args:
        registry_url (str): URL to the UNICORE registry.
        site_name (str): Name of the site to connect to.
        credential (pyunicore.credentials.Credential): Authentication method.

    Raises:
        ValueError: Site not available in the registry.

    Returns:
        pyunicore.client.Client

    """
    site_api_url = _get_site_api_url(
        site=site_name, credential=credential, registry_url=registry_url
    )
    client = _site.connect_to_site(
        site_api_url=site_api_url,
        credential=credential,
    )
    return client


def _get_site_api_url(
    site: str,
    credential: credentials.Credential,
    registry_url: str,
) -> str:
    api_urls = _get_api_urls(credential, registry_url=registry_url)
    try:
        api_url = api_urls[site]
    except KeyError:
        available_sites_list = list(api_urls.keys())
        available_sites = ", ".join(available_sites_list)
        raise ValueError(
            f"Site {site} not available in registry {registry_url}. "
            f"Available sites: {available_sites}."
        )
    return api_url


def _get_api_urls(credential: credentials.Credential, registry_url: str) -> Dict[str, str]:
    registry = pyunicore.client.Registry(credential, url=registry_url)
    return registry.site_urls
