import json
import unittest

import pyunicore.aio.client as uc_client
import pyunicore.credentials as uc_credentials


class TestAsyncBasic(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        pass

    def get_client(self, credential=None) -> uc_client.Client:
        if credential is None:
            credential = uc_credentials.UsernamePassword("demouser", "test123")
        base_url = "https://localhost:8080/DEMO-SITE/rest/core"
        transport = uc_client.Transport(credential)
        return uc_client.Client(transport, base_url)

    async def test_connect(self):
        print("*** test_connect")
        async with self.get_client() as client:
            p = await client.properties
            print(json.dumps(p["client"], indent=2))
            self.assertEqual("user", p["client"]["role"]["selected"])
            c = await client.access_info
            self.assertEqual("user", c["role"]["selected"])

    async def test_issue_auth_token(self):
        print("*** test_issue_auth_token")
        async with self.get_client() as client:
            if await client.server_version_info < (9, 2, 0):
                print("Skipping, requires server 9.2.0 or later")
                return
            token = await client.issue_auth_token(lifetime=600, limited=True)
            print("token: %s" % token)

    async def test_list_application(self):
        print("*** test_list_application")
        async with self.get_client() as client:
            for a in await client.get_applications():
                print(f"{a} {await a.name} {await a.version} {await a.options}")


if __name__ == "__main__":
    unittest.main()
