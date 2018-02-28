
import json
import requests

from jwt import decode as jwt_decode, ExpiredSignatureError

class RefreshHandler(object):
    
    def __init__(self, token, refresh_config):
        '''
        token: initial access token
        refresh_config: a dict containing url, client_id, client_secret, refresh_token
        '''
        self.token = token
        self.refresh_config = refresh_config
        
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
        except ExpiredSignatureError as ex:
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
 
    def get_valid_token(self):
        ''' get a valid access token. If necessary, refresh it.
        '''
        if not self.is_valid_token():
            self.refresh()
        return self.token

    
