import os
import unittest

import pyunicore.client as uc_client
import pyunicore.credentials as uc_credentials


class TestBasic(unittest.TestCase):
    def setUp(self):
        pass

    def get_client(self):
        credential = uc_credentials.UsernamePassword("demouser", "test123")
        base_url = "https://localhost:8080/DEMO-SITE/rest/core"
        transport = uc_client.Transport(credential)
        return uc_client.Client(transport, base_url)

    def test_connect(self):
        print("*** test_connect")
        client = self.get_client()
        self.assertEqual("user", client.properties["client"]["role"]["selected"])

    def test_run_date(self):
        print("*** test_run_date")
        client = self.get_client()
        job_desc = {"Executable": "date"}
        job = client.new_job(job_desc)
        print(job)
        job.cache_time = 0
        job.poll()
        exit_code = int(job.properties["exitCode"])
        self.assertEqual(0, exit_code)
        work_dir = job.working_dir
        stdout = work_dir.stat("/stdout").raw().read()
        self.assertTrue(len(stdout) > 0)
        print(stdout)

    def test_run_uploaded_script(self):
        print("*** test_run_uploaded_script")
        client = self.get_client()
        job_desc = {"Executable": "bash", "Arguments": ["script.sh"]}
        in_file = os.getcwd() + "/tests/integration/files/script.sh"
        job = client.new_job(job_desc, [in_file])
        job.poll()
        exit_code = int(job.properties["exitCode"])
        self.assertEqual(0, exit_code)
        work_dir = job.working_dir
        stdout = work_dir.stat("/stdout").raw().read()
        self.assertTrue(len(stdout) > 0)
        print(stdout)

    def test_alloc_and_run_date(self):
        print("*** test_alloc_and_run_date")
        client = self.get_client()
        alloc_desc = {"Job type": "ALLOCATE", "Resources": {"Runtime": "10m"}}
        allocation = client.new_job(alloc_desc)
        try:
            print(allocation)
            allocation.wait_until_available()
            job_desc = {"Executable": "date"}
            job = allocation.new_job(job_desc)
            print(job)
            job.cache_time = 0
            job.poll()
            exit_code = int(job.properties["exitCode"])
            self.assertEqual(0, exit_code)
            work_dir = job.working_dir
            stdout = work_dir.stat("/stdout").raw().read()
            self.assertTrue(len(stdout) > 0)
            print(stdout)
        finally:
            allocation.abort()


if __name__ == "__main__":
    unittest.main()
