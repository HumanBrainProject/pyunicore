"""
    Credentials for authenticating
"""

try:
    from urllib3 import disable_warnings

    disable_warnings()
except ImportError:
    pass

from abc import ABCMeta, abstractmethod
from base64 import b64encode
from jwt import (
    decode as jwt_decode,
    encode as jwt_encode,
    ExpiredSignatureError,
)
import datetime
import requests
from os import getenv
from os.path import isabs


class AuthenticationFailedException(Exception):  # noqa N818
    """User authentication has failed."""


class Credential:
    """
    Base class for credential
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_auth_header(self):
        """returns the value for the HTTP Authorization header"""
        ...


class UsernamePassword(Credential):
    """
    Produces a HTTP Basic authorization header value

    Args:
        username: the username
        password: the password
    """

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_auth_header(self):
        t = f"{self.username}:{self.password}"
        return "Basic " + b64encode(bytes(t, "ascii")).decode("ascii")


class OIDCToken(Credential):
    """
    Produces a header value "Bearer <auth_token>"

    Args:
        token: the value of the auth token
        refresh_handler: optional refresh handler that provides a get_token() method which
                         will be invoked to refresh the bearer token
    """

    def __init__(self, token, refresh_handler=None):
        self.token = token
        self.refresh_handler = refresh_handler

    def get_auth_header(self):
        if self.refresh_handler is not None:
            self.token = self.refresh_handler.get_token()
        return "Bearer " + self.token


class RefreshHandler:
    """helper to refresh an OAuth token"""

    def __init__(self, refresh_config, token=None):
        """
        token: initial access token (can be None)
        refresh_config: a dict containing url, client_id, client_secret, refresh_token
        """
        self.refresh_config = refresh_config
        self.token = token
        if not token:
            self.refresh()

    def is_valid_token(self):
        """
        check if the given token is still valid
        TODO check whether token was revoked
        """
        try:
            jwt_decode(
                self.token,
                options={
                    "verify_signature": False,
                    "verify_nbf": False,
                    "verify_exp": True,
                    "verify_aud": False,
                },
            )
            return True
        except ExpiredSignatureError:
            return False

    def refresh(self):
        """refresh the token"""
        params = dict(
            client_id=self.refresh_config["client_id"],
            client_secret=self.refresh_config["client_secret"],
            refresh_token=self.refresh_config["refresh_token"],
            grant_type="refresh_token",
        )
        url = "%stoken" % self.refresh_config["url"]

        res = requests.post(url, headers={"Accept": "application/json"}, data=params)
        res.raise_for_status()
        self.token = res.json()["access_token"]
        return self.token

    def get_token(self):
        """get a valid access token. If necessary, refresh it."""
        if not self.is_valid_token():
            self.refresh()
        return self.token


class BasicToken(Credential):
    """
    Produces a header value "Basic <auth_token>"

    Args:
        token: the value of the auth token
    """

    def __init__(self, token):
        self.token = token

    def get_auth_header(self):
        return "Basic " + self.token


class Anonymous(Credential):
    """
    Produces no header - anonymous access
    """

    def get_auth_header(self):
        return None


class JWTToken(Credential):
    """
    Produces a signed JWT token ("Bearer <auth_token>")
    uses pyjwt

    Args:
        subject - the subject user name or user X.500 DN
        issuer - the issuer of the token
        secret - a private key or
        algorithm - signing algorithm

        lifetime - token validity time in seconds
        etd - for delegation tokens (servers / services authenticating users), this must be 'True'.
              For end users authenticating, set to 'False'
    """

    def __init__(
        self,
        subject,
        issuer,
        secret,
        algorithm="RS256",
        lifetime=300,
        etd=False,
    ):
        self.subject = subject
        self.issuer = issuer if issuer else subject
        self.lifetime = lifetime
        self.algorithm = algorithm
        self.secret = secret
        self.etd = etd

    def create_token(self):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        payload = {
            "etd": str(self.etd).lower(),
            "sub": self.subject,
            "iss": self.issuer,
            "iat": now,
            "exp": now + datetime.timedelta(seconds=self.lifetime),
        }
        return jwt_encode(payload, self.secret, algorithm=self.algorithm)

    def get_auth_header(self):
        return "Bearer " + self.create_token()


def create_credential(username=None, password=None, token=None, identity=None):
    """Helper to create the most common types of credentials

    Requires one of the following combinations of arguments

    username + password : create a UsernamePassword credential
    token               ; create a OIDCToken credential from the given token
    username + identity : create a JWTToken credential which will be signed
                          with the given private key (ssh key or PEM)
    """

    if token is not None:
        return OIDCToken(token)
    if token is None and identity is None:
        return UsernamePassword(username, password)
    if identity is None:
        raise AuthenticationFailedException("Not enough info to create user credential")
    try:
        from cryptography.hazmat.primitives import serialization

        if not isabs(identity):
            if identity.startswith("~"):
                identity = getenv("HOME") + "/" + identity.lstrip("~")
            else:
                identity = getenv("HOME") + "/.uftp/" + identity
        pem = open(identity).read()
        pem_bytes = bytes(pem, "UTF-8")
        if password is not None and len(password) > 0:
            passphrase = bytes(password, "UTF-8")
        else:
            passphrase = None
        try:
            private_key = serialization.load_ssh_private_key(pem_bytes, password=passphrase)
        except ValueError:
            private_key = serialization.load_pem_private_key(pem_bytes, password=passphrase)
        secret = private_key
        sub = username
        algo = "EdDSA"
        if "BEGIN RSA" in pem:
            algo = "RS256"
        elif "BEGIN EC" in pem or "PuTTY" in pem:
            algo = "ES256"
        return JWTToken(sub, sub, secret, algorithm=algo, etd=False)
    except ImportError:
        raise AuthenticationFailedException(
            "To use key-based authentication, you will need the 'cryptography' package."
        )
