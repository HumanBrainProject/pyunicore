import unittest

import pyunicore.cli.base as base


class TestBase(unittest.TestCase):

    def test_base_setup(self):
        cmd = base.Base()
        cmd.config_file = "tests/integration/cli/preferences"
        cmd.load_user_properties()
        registry = cmd.create_registry()
        self.assertTrue(len(registry.site_urls) > 0)
        print(registry.site_urls)

    def test_issue_token(self):
        cmd = base.IssueToken()
        config_file = "tests/integration/cli/preferences"
        ep = "https://localhost:8080/DEMO-SITE/rest/core"
        args = ["-c", config_file, ep, "--lifetime", "700", "--inspect", "--limited", "--renewable"]
        cmd.run(args)

    def test_rest_get(self):
        cmd = base.REST()
        config_file = "tests/integration/cli/preferences"
        ep = "https://localhost:8080/DEMO-SITE/rest/core"
        args = ["-c", config_file, "GET", ep]
        cmd.run(args)

    def test_rest_post_put_delete(self):
        cmd = base.REST()
        config_file = "tests/integration/cli/preferences"
        ep = "https://localhost:8080/DEMO-SITE/rest/core/sites"
        d = "{}"
        args = ["-c", config_file, "--data", d, "POST", ep]
        cmd.run(args)
        d = "{'tags': 'test123'}"
        ep = cmd._last_location
        args = ["-c", config_file, "--data", d, "PUT", ep]
        cmd.run(args)
        args = ["-c", config_file, "DELETE", ep]
        cmd.run(args)


if __name__ == "__main__":
    unittest.main()
