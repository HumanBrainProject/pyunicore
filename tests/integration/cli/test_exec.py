import unittest

import pyunicore.cli.exec as exec


class TestExec(unittest.TestCase):

    def test_exec(self):
        cmd = exec.Exec()
        config_file = "tests/integration/cli/preferences"
        ep = "https://localhost:8080/DEMO-SITE/rest/core"
        args = ["-c", config_file, "-v", "--keep", "--server-url", ep, "date"]
        cmd.run(args)

    def test_run_1(self):
        cmd = exec.Run()
        config_file = "tests/integration/cli/preferences"
        ep = "https://localhost:8080/DEMO-SITE/rest/core"
        jobfile = "tests/integration/cli/jobs/date.u"
        args = ["-c", config_file, "-v", "--server-url", ep, jobfile]
        cmd.run(args)

    def test_list_jobs(self):
        cmd = exec.ListJobs()
        config_file = "tests/integration/cli/preferences"
        args = ["-c", config_file, "-v", "-l"]
        cmd.run(args)


if __name__ == "__main__":
    unittest.main()
