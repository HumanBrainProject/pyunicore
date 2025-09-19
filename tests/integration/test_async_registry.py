import unittest

import pyunicore.aio.client as uc_client
import pyunicore.credentials as uc_credentials


class TestRegistry(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        pass

    def get_registry(self):
        credential = uc_credentials.UsernamePassword("demouser", "test123")
        base_url = "https://localhost:8080/DEMO-SITE/rest/registries/default_registry"
        transport = uc_client.Transport(credential)
        return uc_client.Registry(transport, base_url)

    async def test_connect(self):
        print("*** test_connect")
        async with self.get_registry() as registry:
            print("Registry contains: ", await registry.site_urls)
            site_client = await registry.site("DEMO-SITE")
            self.assertEqual("user", (await site_client.properties)["client"]["role"]["selected"])
            if len(await registry.workflow_services_urls) > 0:
                workflow_client = await registry.workflow_service("DEMO-SITE")
                self.assertEqual(
                    "user", (await workflow_client.properties)["client"]["role"]["selected"]
                )
            else:
                print("No workflow services in registry.")


if __name__ == "__main__":
    unittest.main()
