import logging

import pyunicore.client

from . import transport as _transport
from . import authorization as _authorization

logger = logging.getLogger(__name__)


class AuthorizationFailedException(Exception):
    """User authorization has failed.

    Unfortunately the response by the server does not give any detailed
    information why the authorization fails.

    """


def connect_to_site(
    site_api_url: str,
    authorization: _authorization.Authorization,
) -> pyunicore.client.Client:
    """Create a connection to a site's UNICORE API.

    Args:
        site_api_url (str): REST API URL to the cluster's UNICORE server.
        authorization (pyunicore.helpers.Authorization): authorization method

    Raises:
        AuthorizationFailedException: Authorization on the cluster failed.

    Returns:
        pyunicore.client.Client

    """
    logger.info("Attempting to connect to %s", site_api_url)
    client = _connect_to_site(
        api_url=site_api_url,
        authorization=authorization,
    )
    if _authorization_failed(client):
        raise AuthorizationFailedException(
            "Check if user and password are correct, and if the cluster name "
            "and registry URL are correct."
        )
    logger.info("Successfully connected to %s", site_api_url)
    return client


def _connect_to_site(
    api_url: str,
    authorization: _authorization.Authorization,
) -> pyunicore.client.Client:
    transport = _transport.create_transport(authorization)
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


def _authorization_failed(client: pyunicore.client.Client) -> bool:
    logger.debug(
        "Connection login information: %s",
        client.properties["client"]["xlogin"],
    )
    return False if client.properties["client"]["xlogin"] else True
