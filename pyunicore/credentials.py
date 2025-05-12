"""
    Credentials for authenticating
"""

try:
    from urllib3 import disable_warnings

    disable_warnings()
except ImportError:
    pass

import datetime
import getpass
import json
import socket
from abc import ABCMeta
from abc import abstractmethod
from base64 import b64encode
from contextlib import closing
from os import environ
from os import getenv
from os.path import isabs
from os.path import isfile

import requests
from jwt import encode as jwt_encode


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


class Anonymous(Credential):
    """
    Produces no header - anonymous access
    """

    def get_auth_header(self):
        return None


class BasicToken(Credential):
    """
    Produces a header value "Basic <auth_token>"

    Args:
        token: the value of the auth token
    """

    def __init__(self, token):
        self.token = token

    def get_auth_header(self):
        return "Basic " + self.get_token()

    def get_token(self):
        return self.token


class BearerToken(Credential):
    """
    Produces a header value "Bearer <auth_token>"

    Args:
        token: the value of the auth token
    """

    def __init__(self, token):
        self.token = token

    def get_auth_header(self):
        return "Bearer " + self.get_token()

    def get_token(self):
        return self.token


class UsernamePassword(BasicToken):
    """
    Produces a HTTP Basic authorization header value from
    the given username and password

    Args:
        username: the username
        password: the password
    """

    def __init__(self, username, password):
        self.username = username
        self.token = b64encode(bytes(f"{username}:{password}", "ascii")).decode("ascii")


class RefreshHandler:
    """helper to refresh an OAuth token"""

    __metaclass__ = ABCMeta

    @abstractmethod
    def refresh_token(self):
        """returns a valid access token (refreshing it if necessary)"""
        ...


class OIDCToken(BearerToken):
    """
    Produces a header value "Bearer <auth_token>"

    Args:
        token: the (intial) value of the access token
        refresh_handler: optional refresh handler that provides a refresh_token()
                         method which will be invoked to refresh the bearer token
    """

    def __init__(self, token: str, refresh_handler: RefreshHandler = None):
        super().__init__(token)
        self.refresh_handler = refresh_handler

    def get_token(self):
        if self.refresh_handler is not None:
            self.token = self.refresh_handler.refresh_token()
        return self.token


class JWTToken(BearerToken):
    """
    Produces a signed JWT token ("Bearer <auth_token>")

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

    def get_token(self):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        payload = {
            "etd": str(self.etd).lower(),
            "sub": self.subject,
            "iss": self.issuer,
            "iat": now,
            "exp": now + datetime.timedelta(seconds=self.lifetime),
        }
        self.token = jwt_encode(payload, self.secret, algorithm=self.algorithm)
        return self.token


class OIDCAgentToken(OIDCToken):
    """
    Produces a header value "Bearer <auth_token>"
    The token is retrieved from a running oidc-agent
    (https://indigo-dc.gitbook.io/oidc-agent)

    Args:
        account_name: the account to use
    """

    def __init__(self, account_name):
        super().__init__(token=None, refresh_handler=None)
        self.account = account_name

    def get_token(self) -> str:
        params = dict(account=self.account, request="access_token")
        try:
            socket_path = environ.get("OIDC_SOCK")
        except KeyError:
            raise OSError("OIDC Agent not running (environment variable OIDC_SOCK not found)")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(socket_path)
            sock.sendall(json.dumps(params).encode("utf-8"))
            res = b""
            while True:
                part = sock.recv(4096)
                res += part
                if len(part) < 4096:
                    break
            reply = json.loads(res.decode("utf-8"))
            if "success" == reply.get("status", None):
                self.token = reply["access_token"]
        return self.token


class OIDCServerToken(OIDCToken):
    """
    Produces a header value "Bearer <auth_token>"
    The token is retrieved from an OIDC server (e.g. Keycloak)

    Args:
        config: dictionary with configuration items

        oidc.endpoint: OIDC token endpoint
        oidc.username: username
        oidc.password: password. If not set, it will be queried via getpass
        oidc.otp: OTP value for 2FA. If set to 'QUERY', it will be queried via getpass
        oidc.grantType: OIDC grant type (default: 'password')
        oidc.scope: OIDC scope (default: 'openid')
        oidc.storeRefreshToken: whether to store the refresh token (default: 'true')
        oidc.refreshTokenFile: file name for refresh tokens (default: '$HOME/.ucc/refresh-tokens')
    """

    def __init__(self, config: dict):
        super().__init__(token=None, refresh_handler=None)
        self.config = config
        self.refresh_token = None
        self.load_refresh_token()

    def get_token(self) -> str:
        self.check_refresh()
        if self.token is not None:
            return self.token
        username = self.config["oidc.username"]
        password = self.config.get("oidc.password")
        if password is None:
            password = getpass.getpass("OIDC server password for '%s': " % username)
        params = dict(
            grant_type=self.config.get("oidc.grantType", "password"),
            username=username,
            password=password,
            scope=self.config.get("oidc.scope", "openid"),
        )
        otp = self.config.get("oidc.otp")
        if otp == "QUERY":
            otp = getpass.getpass("OTP: ")
        if otp is not None:
            params["otp"] = otp
        response = self._execute_call(params)
        self._handle_response(response)
        return self.token

    def check_refresh(self):
        if self.refresh_token is None:
            return
        params = dict(grant_type="refresh_token", refresh_token=self.refresh_token)
        try:
            response = self._execute_call(params)
            self._handle_response(response)
        except requests.HTTPError:
            pass

    def load_refresh_token(self):
        """if available, use the refresh token"""
        if not self.config.get("oidc.storeRefreshToken", True):
            return
        token_filename = self.config.get("oidc.refreshTokenFile")
        if token_filename is None:
            token_filename = environ.get("HOME") + ".ucc/refresh-tokens"
        refresh_tokens = {}
        if isfile(token_filename):
            with open(token_filename) as f:
                refresh_tokens = json.load(f)
                endpoint = self.config["oidc.endpoint"]
                ep_info = refresh_tokens.get(endpoint)
                if ep_info is not None:
                    self.refresh_token = ep_info.get("refresh_token")
        return refresh_tokens

    def store_refresh_token(self):
        """store the refresh token"""
        if not self.config.get("oidc.storeRefreshToken", True):
            return
        if self.refresh_token is None:
            return
        token_filename = self.config.get("oidc.refreshTokenFile")
        if token_filename is None:
            token_filename = environ.get("HOME") + ".ucc/refresh-tokens"
        refresh_tokens = self.load_refresh_token()
        endpoint = self.config["oidc.endpoint"]
        refresh_tokens[endpoint] = {"refresh_token": self.refresh_token}
        with open(token_filename, "w") as f:
            f.write(json.dumps(refresh_tokens))

    def _execute_call(self, params):
        endpoint = self.config["oidc.endpoint"]
        auth: Credential = None
        auth_mode = self.config.get("oidc.authentication", "POST").upper()
        if auth_mode == "POST":
            params["client_id"] = self.config["oidc.clientID"]
            params["client_secret"] = self.config["oidc.clientSecret"]
        else:
            auth = UsernamePassword(self.config["oidc.clientID"], self.config["oidc.clientSecret"])
        headers = {}
        if auth is not None:
            headers["Authorization"] = auth.get_auth_header()
        with closing(requests.post(endpoint, data=params, headers=headers)) as response:
            response.raise_for_status()
            return response.json()

    def _handle_response(self, response: dict):
        self.refresh_token = response.get("refresh_token")
        self.store_refresh_token()
        self.token = response.get("access_token")


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
