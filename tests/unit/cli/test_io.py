import unittest

import pyunicore.cli.io as io


class TestIO(unittest.TestCase):

    def test_split_path(self):
        tests = {
            "/foo/*": ("/foo", "*"),
            "/foo/test.txt": ("/foo", "test.txt"),
            "test.txt": ("/", "test.txt"),
            "/test.txt": ("/", "test.txt"),
            "/foo/bar/test.txt": ("/foo/bar", "test.txt"),
        }
        for p in tests:
            base, pattern = io.split_path(p)
            self.assertEqual((base, pattern), tests[p])

    def test_normalize(self):
        tests = {
            "/foo//bar": "/foo/bar",
        }
        for p in tests:
            self.assertEqual(io.normalized(p), tests[p])


if __name__ == "__main__":
    unittest.main()
