import unittest

import pyunicore.cli.base as base
from pyunicore.credentials import UsernamePassword


class TestBase(unittest.TestCase):
    def test_base_setup(self):
        cmd = base.Base()
        cmd.config_file = "tests/unit/cli/preferences"
        cmd.load_user_properties()
        self.assertEqual(
            "https://localhost:8080/DEMO-SITE/rest/registries/default_registry",
            cmd.config["registry"],
        )
        cmd.create_credential()
        self.assertTrue(isinstance(cmd.credential, UsernamePassword))


if __name__ == "__main__":
    unittest.main()
