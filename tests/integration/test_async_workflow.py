import asyncio
import json
import unittest

import pyunicore.aio.client as uc_client
import pyunicore.credentials as uc_credentials


class TestAsyncWorkflow(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        pass

    def get_client(self) -> uc_client.WorkflowService:
        credential = uc_credentials.UsernamePassword("demouser", "test123")
        base_url = "https://localhost:8080/DEMO-SITE/rest/workflows"
        return uc_client.WorkflowService(credential, base_url)

    async def read_file(self, wf: uc_client.Workflow, name: str) -> str:
        p = await wf.stat(name)
        if isinstance(p, uc_client.PathFile):
            return await p.read()

    async def test_run_workflow(self):
        print("*** test_run_workflow")
        async with self.get_client() as wf_service:
            with open("tests/integration/files/workflow1.json") as _f:
                wf = json.load(_f)
            wf1 = await wf_service.new_workflow(wf)
            print("Submitted %s" % wf1.resource_url)
            print("... waiting for workflow to go into HELD state")
            while not await wf1.is_held:
                await asyncio.sleep(2)
            params = await wf1.parameters
            print("... workflow variables: %s" % params)
            params["COUNTER"] = "789"
            print("... resuming workflow with params = %s" % params)
            await wf1.resume(params)
            print("... waiting for workflow to finish")
            await wf1.poll()
            params = await wf1.parameters
            print("Final workflow variables: %s" % params)
            self.assertEqual("789", params["COUNTER"])
            self.assertEqual(2, len(await wf1.get_files()))
            self.assertEqual(2, len(await wf1.get_jobs()))

            print("Output from date1: %s " % await self.read_file(wf1, "wf:date1/stdout"))
            print("Output from date2: %s " % await self.read_file(wf1, "wf:date2/stdout"))


if __name__ == "__main__":
    unittest.main()
