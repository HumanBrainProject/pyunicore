import unittest

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


if __name__ == "__main__":
    unittest.main()
