import logging

import pyunicore.client

from . import transport as _transport

logger = logging.getLogger(__name__)


class AuthenticationFailedException(Exception):
    """User authentication has failed.

    Unfortunately the response by the server does not give any detailed
    information why the authentication fails.

    """


def connect_to_site(
    site_api_url: str,
    user: str,
    password: str,
) -> pyunicore.client.Client:
    """Create a connection to a site's UNICORE API.

    Args:
        site_api_url (str): REST API URL to the cluster's UNICORE server.
        user (str): JUDOOR user name.
        password (str): Corresponding JUDOOR user password.

    Raises:
        AuthenticationFailedException: Authentication on the cluster failed.

    Returns:
        pyunicore.client.Client

    """
    logger.info("Attempting to connect to %s", site_api_url)
    connection = _connect_to_site(
        api_url=site_api_url,
        user=user,
        password=password,
    )
    if _authentication_failed(connection):
        raise AuthenticationFailedException(
            "Check if user and password are correct, and if the cluster name "
            "and registry URL are correct."
        )
    logger.info("Successfully connected to %s", site_api_url)
    return connection


def _connect_to_site(
    api_url: str,
    user: str,
    password: str,
) -> pyunicore.client.Client:
    transport = _transport.create_transport(user=user, password=password)
    client = _create_client(transport=transport, api_url=api_url)
    logger.debug("Connection properties: %s", client.properties)
    return client


def _create_client(
    transport: pyunicore.client.Transport, api_url: str
) -> pyunicore.client.Client:
    logger.debug("Creating client connection using REST API URL %s", api_url)
    client = pyunicore.client.Client(transport=transport, site_url=api_url)
    logger.debug("Client properties: %s", client.properties)
    return client


def _authentication_failed(client: pyunicore.client.Client) -> bool:
    logger.debug(
        "Connection login information: %s",
        client.properties["client"]["xlogin"],
    )
    return False if client.properties["client"]["xlogin"] else True
