import asyncio
import os
import unittest

import pyunicore.aio.client as uc_client
import pyunicore.credentials as uc_credentials


class TestAsyncJob(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        pass

    def get_client(self, credential=None) -> uc_client.Client:
        if credential is None:
            credential = uc_credentials.UsernamePassword("demouser", "test123")
        base_url = "https://localhost:8080/DEMO-SITE/rest/core"
        transport = uc_client.Transport(credential)
        return uc_client.Client(transport, base_url)

    async def test_run_date(self):
        print("*** test_run_date")
        async with self.get_client() as client:
            job_desc = {"Executable": "date"}
            job = await client.new_job(job_desc)
            print(job)
            await job.poll()
            self.assertFalse(await job.is_running)
            exit_code = await job.exit_code
            self.assertEqual(0, exit_code)
            log = await job.log
            self.assertTrue(len(log) > 0)
            work_dir = await job.working_dir
            stdout = await work_dir.stat("/stdout")
            _txt = await stdout.read()
            self.assertTrue(len(_txt) > 0)
            print(_txt)

    async def test_exec_date(self):
        print("*** test_exec_date")
        async with self.get_client() as client:
            job = await client.execute("date")
            print(job)
            job.cache_time = 0
            await job.poll()
            exit_code = await job.exit_code
            self.assertEqual(0, exit_code)
            work_dir = await job.working_dir
            stdout = await work_dir.stat("/stdout")
            _txt = await stdout.read()
            self.assertTrue(len(_txt) > 0)
            print(_txt)
            print("*** ++ restarting")
            await job.restart()
            await asyncio.sleep(5)
            await job.poll()
            exit_code = await job.exit_code
            self.assertEqual(0, exit_code)
            self.assertFalse(await job.is_running)
            _txt2 = await stdout.read()
            print(_txt2)
            self.assertNotEqual(_txt2, _txt)

    async def test_run_uploaded_script(self):
        print("*** test_run_uploaded_script")
        async with self.get_client() as client:
            job_desc = {"Executable": "bash", "Arguments": ["script.sh"]}
            in_file = os.getcwd() + "/tests/integration/files/script.sh"
            job = await client.new_job(job_desc, [in_file])
            await job.poll()
            exit_code = await job.exit_code
            self.assertEqual(0, exit_code)
            work_dir = await job.working_dir
            stdout = await (await work_dir.stat("/stdout")).read()
            self.assertTrue(len(stdout) > 0)
            print(stdout)

    async def test_run_uploaded_script_2(self):
        print("*** test_run_uploaded_script_2")
        async with self.get_client() as client:
            job_desc = {"Executable": "bash", "Arguments": ["myscript.sh"]}
            in_file = os.getcwd() + "/tests/integration/files/script.sh"
            job = await client.new_job(job_desc, {"myscript.sh": in_file})
            await job.poll()
            exit_code = await job.exit_code
            self.assertEqual(0, exit_code)
            work_dir = await job.working_dir
            stdout = await (await work_dir.stat("/stdout")).read()
            self.assertTrue(len(stdout) > 0)
            print(stdout)

    async def test_alloc_and_run_date(self):
        print("*** test_alloc_and_run_date")
        async with self.get_client() as client:
            alloc_desc = {"Job type": "ALLOCATE", "Resources": {"Runtime": "10m"}}
            allocation: uc_client.Allocation = await client.new_job(alloc_desc)
            try:
                print(allocation)
                await allocation.wait_until_available()
                if (await allocation.status) != uc_client.JobStatus.RUNNING:
                    print("Skipping, allocation not available.")
                    return
                job_desc = {"Executable": "date"}
                job = await allocation.new_job(job_desc)
                print(job)
                await job.poll()
                exit_code = await job.exit_code
                self.assertEqual(0, exit_code)
                work_dir = await job.working_dir
                stdout = await (await work_dir.stat("/stdout")).read()
                self.assertTrue(len(stdout) > 0)
                print(stdout)
            finally:
                await allocation.abort()


if __name__ == "__main__":
    unittest.main()
