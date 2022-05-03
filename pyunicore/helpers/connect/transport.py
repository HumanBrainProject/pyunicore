import base64
import logging
import functools
from typing import Tuple

import pyunicore.client

from . import authorization as _authorization

logger = logging.getLogger(__name__)


def create_transport(
    authorization: _authorization.Authorization,
) -> pyunicore.client.Transport:
    """Create a `pyunicore.client.Transport` for authorization.

    Args:
        authorization (pyunicore.helpers.Authorization): authorization method

    Returns:
        pyunicore.client.Transport

    """
    token, is_bearer_token = _create_token(authorization)
    return pyunicore.client.Transport(auth_token=token, oidc=is_bearer_token)


@functools.singledispatch
def _create_token(
    authorization: _authorization.Authorization,
) -> Tuple[str, bool]:
    raise NotImplementedError("Unsupported authorization method")


@_create_token.register(_authorization.UserAuthorization)
def _create_token_for_user_auth(
    authorization: _authorization.UserAuthorization,
) -> Tuple[str, bool]:
    token = f"{authorization.user}:{authorization.password}".encode()
    is_bearer_token = False
    return base64.b64encode(token).decode("ascii"), is_bearer_token


@_create_token.register(_authorization.TokenAuthorization)
def _create_token_for_token_auth(
    authorization: _authorization.TokenAuthorization,
) -> Tuple[str, bool]:
    is_bearer_token = True
    return authorization.token, is_bearer_token
