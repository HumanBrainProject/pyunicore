import json, unittest

import credentials
from client import Transport
from base64 import b64encode
from builtins import object
        
class TestCredentials(unittest.TestCase):
    def setUp(self):
        pass

    def test_username_password(self):
        print("*** test_username_password")
        credential = credentials.UsernamePassword("demouser", "test123")
        self.assertEqual("Basic "+b64encode(b"demouser:test123").decode("ascii"),
                         credential.get_auth_header())

    def test_oidc_token(self):
        print("*** test_oidc_token")
        credential = credentials.OIDCToken("test123")
        self.assertEqual("Bearer test123", credential.get_auth_header())

    def test_oidc_token_with_refresh(self):
        print("*** test_oidc_token_with_refresh")
        refresh_handler = MockRefresh()
        credential = credentials.OIDCToken("test123", refresh_handler)
        self.assertEqual("Bearer foobar", credential.get_auth_header())

    def test_basic_token(self):
        print("*** test_basic_token")
        credential = credentials.BasicToken("test123")
        self.assertEqual("Basic test123", credential.get_auth_header())

    def test_transport(self):
        print("*** test_transport")
        token_str = b64encode(b"demouser:test123").decode("ascii")
        header_val = "Basic "+token_str
        credential = credentials.UsernamePassword("demouser", "test123")
        transport = Transport(credential)
        self.assertEqual(header_val, transport._headers({})['Authorization'])
        # old style
        transport = Transport(token_str, oidc=False)
        self.assertEqual(header_val, transport._headers({})['Authorization'])
        transport2 = transport._clone()
        self.assertEqual(header_val, transport2._headers({})['Authorization'])


class MockRefresh(object):
    def get_token(self):
        return "foobar"

if __name__ == '__main__':
    unittest.main()
