import base64
import logging
import functools
from typing import Tuple

import pyunicore.client

from pyunicore.helpers.connect import authentication as _authentication

logger = logging.getLogger(__name__)


def create_transport(
    authentication: _authentication.Authentication,
) -> pyunicore.client.Transport:
    """Create a `pyunicore.client.Transport` for authentication.

    Args:
        authentication (pyunicore.helpers.Authentication): authentication method

    Returns:
        pyunicore.client.Transport

    """
    token, is_bearer_token = _create_token(authentication)
    return pyunicore.client.Transport(auth_token=token, oidc=is_bearer_token)


@functools.singledispatch
def _create_token(
    authentication: _authentication.Authentication,
) -> Tuple[str, bool]:
    raise NotImplementedError("Unsupported authentication method")


@_create_token.register(_authentication.UserAuthentication)
def _create_token_for_user_auth(
    authentication: _authentication.UserAuthentication,
) -> Tuple[str, bool]:
    token = f"{authentication.user}:{authentication.password}".encode()
    is_bearer_token = False
    return base64.b64encode(token).decode("ascii"), is_bearer_token


@_create_token.register(_authentication.TokenAuthentication)
def _create_token_for_token_auth(
    authentication: _authentication.TokenAuthentication,
) -> Tuple[str, bool]:
    is_bearer_token = True
    return authentication.token, is_bearer_token
