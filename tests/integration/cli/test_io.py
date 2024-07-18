import unittest

import pyunicore.cli.base as base
import pyunicore.cli.io as io
import pyunicore.client


class TestIO(unittest.TestCase):

    def test_crawl(self):
        cmd = base.Base()
        cmd.config_file = "tests/integration/cli/preferences"
        cmd.load_user_properties()
        ep = "https://localhost:8080/DEMO-SITE/rest/core/storages/HOME"
        registry = cmd.create_registry()
        self.assertTrue(len(registry.site_urls) > 0)
        storage = pyunicore.client.Storage(registry.transport, ep)
        for x in io.crawl_remote(storage, "/", "*"):
            print(x)

    def test_ls(self):
        cmd = io.LS()
        config_file = "tests/integration/cli/preferences"
        ep = "https://localhost:8080/DEMO-SITE/rest/core/storages/HOME"
        args = ["-c", config_file, "-v", "--long", ep]
        cmd.run(args)


if __name__ == "__main__":
    unittest.main()
