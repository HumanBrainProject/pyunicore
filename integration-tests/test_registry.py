import pyunicore.client as uc_client
import pyunicore.credentials as uc_credentials
import json, os, unittest

class TestBasic(unittest.TestCase):
    def setUp(self):
        pass

    def get_client(self):
        credential = uc_credentials.UsernamePassword("demouser", "test123")
        base_url = "https://localhost:8080/DEMO-SITE/rest/registries/default_registry"
        transport  = uc_client.Transport(credential)
        return uc_client.Registry(transport, base_url)

    def test_connect(self):
        print("*** test_connect")
        registry = self.get_client()
        site_client = registry.site("DEMO-SITE")
        self.assertEqual("user", site_client.properties['client']['role']['selected'])
        workflow_client = registry.workflow_service("DEMO-SITE")
        self.assertEqual("user", workflow_client.properties['client']['role']['selected'])


if __name__ == '__main__':
    unittest.main()
