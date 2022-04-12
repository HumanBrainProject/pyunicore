import base64
import logging

import pyunicore.client

logger = logging.getLogger(__name__)


def create_transport(user: str, password: str) -> pyunicore.client.Transport:
    """Create a `pyunicore.client.Transport` for authorization.

    Args:
        user (str): User name for authorization.
        password (str): Password for authorization.

    """
    token = _create_token(user=user, password=password)
    return pyunicore.client.Transport(auth_token=token, oidc=False)


def _create_token(user: str, password: str) -> str:
    token = f"{user}:{password}".encode()
    return base64.b64encode(token).decode("ascii")
