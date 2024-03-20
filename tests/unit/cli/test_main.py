import unittest

import pyunicore.cli.main as main


class TestMain(unittest.TestCase):
    def test_help(self):
        main.help()
        main.show_version()
        for cmd in main._commands:
            print("\n*** %s *** " % cmd)
            c = main.get_command(cmd)
            print(c.get_synopsis())
            c.parser.print_usage()
            c.parser.print_help()

    def test_run_args(self):
        main.run([])
        main.run(["--version"])
        main.run(["--help"])
        try:
            main.run(["no-such-cmd"])
            self.fail()
        except ValueError:
            pass


if __name__ == "__main__":
    unittest.main()
