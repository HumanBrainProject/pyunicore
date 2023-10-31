import json
import os
import unittest

import pyunicore.client as uc_client
import pyunicore.credentials as uc_credentials


class TestAuth(unittest.TestCase):
    def setUp(self):
        pass

    def get_client(self, credential=None):
        if credential is None:
            credential = uc_credentials.UsernamePassword("demouser", "test123")
        base_url = "https://localhost:8080/DEMO-SITE/rest/core"
        transport = uc_client.Transport(credential)
        return uc_client.Client(transport, base_url)
        print("token: %s" % token)

    def test_username_auth(self):
        print("*** test_username_auth")
        client = self.get_client()
        print(json.dumps(client.access_info(), indent=2))
        self.assertEqual("user", client.properties["client"]["role"]["selected"])

    def test_anonymous_info(self):
        print("*** test_anonymous_info")
        cred = uc_credentials.Anonymous()
        client = self.get_client(cred)
        self.assertEqual("anonymous", client.properties["client"]["role"]["selected"])

    def test_issue_auth_token(self):
        print("*** test_issue_auth_token")
        client = self.get_client()
        if client.server_version_info() < (9, 2, 0):
            print("Skipping, requires server 9.2.0 or later")
            return
        token = client.issue_auth_token(lifetime=600, limited=True)
        print("token: %s" % token)

if __name__ == "__main__":
    unittest.main()
