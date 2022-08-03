"""
    Credentials for authenticating
"""

from abc import ABCMeta, abstractmethod
from base64 import b64encode
from jwt import decode as jwt_decode, ExpiredSignatureError
import requests

try:
    from urllib3 import disable_warnings
    disable_warnings()
except:
    pass


class Credential(object):
    """
    Base class for credential
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_auth_header(self):
        """ returns the value for the HTTP Authorization header """
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
        t = "%s:%s" % (self.username, self.password)
        return "Basic "+b64encode(bytes(t, "ascii")).decode("ascii")

class OIDCToken(Credential):
    """
    Produces a header value "Bearer <auth_token>"

    Args:
        token: the value of the auth token
        refresh_handler: optional refresh handler that provides a get_token() method which
                         will be invoked to refresh the bearer token
    """
    def __init__(self, token, refresh_handler = None):
        self.token = token
        self.refresh_handler= refresh_handler
    
    def get_auth_header(self):
        if self.refresh_handler is not None:
            self.token = self.refresh_handler.get_token()
        return "Bearer "+self.token


class RefreshHandler(object):
    ''' helper to refresh an OAuth token '''
    def __init__(self, refresh_config, token = None):
        '''
        token: initial access token (can be None)
        refresh_config: a dict containing url, client_id, client_secret, refresh_token
        '''
        self.refresh_config = refresh_config
        self.token = token
        if not token:
            self.refresh()

    def is_valid_token(self):
        '''
        check if the given token is still valid
        TODO check whether token was revoked
        '''
        try:
            jwt_decode(self.token, options={'verify_signature': False,
                                   'verify_nbf': False,
                                   'verify_exp': True,
                                   'verify_aud': False})
            return True
        except ExpiredSignatureError:
            return False

    def refresh(self):
        ''' refresh the token '''
        params = dict(
            client_id=self.refresh_config['client_id'],
            client_secret=self.refresh_config['client_secret'],
            refresh_token=self.refresh_config['refresh_token'],
            grant_type='refresh_token'
        )
        url = "%stoken" % self.refresh_config['url']
        
        res = requests.post(url,headers={"Accept": "application/json"}, data=params)
        res.raise_for_status()
        self.token = res.json()['access_token']
        return self.token
 
    def get_token(self):
        ''' get a valid access token. If necessary, refresh it.
        '''
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
        return "Basic "+self.token
