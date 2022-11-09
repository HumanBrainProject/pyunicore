import pyunicore.client
from pyunicore import credentials as _credentials


def connect_to_site(
    site_api_url: str, credentials: _credentials.Credential
) -> pyunicore.client.Client:
    """Create a connection to a site's UNICORE API.

    Args:
        site_api_url (str): REST API URL to the cluster's UNICORE server.
        credentials (pyunicore.credentials.Credential): Authentication method.

    Raises:
        pyunicore.credentials.AuthenticationFailedException: Authentication on the cluster failed.

    Returns:
        pyunicore.client.Client

    """
    client = _connect_to_site(
        api_url=site_api_url,
        credentials=credentials,
    )
    if _authentication_failed(client):
        raise _credentials.AuthenticationFailedException(
            "Check if your credentials are correct, and if the cluster name "
            "and registry URL are correct."
        )
    return client


def _connect_to_site(api_url: str, credentials: _credentials.Credential) -> pyunicore.client.Client:
    transport = pyunicore.client.Transport(credentials)
    client = _create_client(transport=transport, api_url=api_url)
    return client


def _create_client(transport: pyunicore.client.Transport, api_url: str) -> pyunicore.client.Client:
    return pyunicore.client.Client(transport=transport, site_url=api_url)


def _authentication_failed(client: pyunicore.client.Client) -> bool:
    return False if client.properties["client"]["xlogin"] else True
