import unittest
from os import environ

from pyunicore.uftpfs import UFTPOpener


class TestUFTPFS(unittest.TestCase):
    def setUp(self):
        pass

    def test_parse_url(self):
        print("*** test_parse_url")
        u1 = "localhost:9000/rest/auth/TEST:/data-dir"
        auth_url, base_dir = UFTPOpener()._parse(u1)
        self.assertEqual("https://localhost:9000/rest/auth/TEST", auth_url)
        self.assertEqual("/data-dir", base_dir)

    def test_credential_username_password(self):
        print("*** test_credential_username_password")
        parse_result = P()
        cred = UFTPOpener()._create_credential(parse_result)
        self.assertEqual(cred.username, "demouser")
        self.assertEqual(cred.password, "test123")

    def test_credential_token(self):
        print("*** test_credential_token")
        parse_result = P()
        parse_result.username = None
        parse_result.password = None
        parse_result.params["token"] = "some_token"
        cred = UFTPOpener()._create_credential(parse_result)
        self.assertEqual(cred.token, "some_token")
        parse_result.params["token"] = "@tests/unit/token.txt"
        cred = UFTPOpener()._create_credential(parse_result)
        self.assertEqual(cred.token, "some_token")
        parse_result.params["token"] = "@@MY_VAR"
        environ["MY_VAR"] = "some_token"
        cred = UFTPOpener()._create_credential(parse_result)
        self.assertEqual(cred.token, "some_token")


class P:
    def __init__(self):
        self.username = "demouser"
        self.password = "test123"
        self.params = {}


if __name__ == "__main__":
    unittest.main()
