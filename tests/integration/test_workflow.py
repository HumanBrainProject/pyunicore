import json
import unittest
from time import sleep

import pyunicore.client as uc_client
import pyunicore.credentials as uc_credentials


class TestBasic(unittest.TestCase):
    def setUp(self):
        pass

    def get_client(self):
        credential = uc_credentials.UsernamePassword("demouser", "test123")
        base_url = "https://localhost:8080/DEMO-SITE/rest/workflows"
        transport = uc_client.Transport(credential)
        return uc_client.WorkflowService(transport, base_url)

    def test_run_workflow(self):
        print("*** test_run_workflow")
        wf_service = self.get_client()
        with open("tests/integration/files/workflow1.json") as _f:
            wf = json.load(_f)
        workflow1 = wf_service.new_workflow(wf)
        print("Submitted %s" % workflow1.resource_url)
        print("... waiting for workflow to go into HELD state")
        while not workflow1.is_held():
            sleep(2)
        params = workflow1.properties["parameters"]
        print("... workflow variables: %s" % params)
        params["COUNTER"] = "789"
        print("... resuming workflow with params = %s" % params)
        workflow1.resume(params)
        print("... waiting for workflow to finish")
        workflow1.poll()
        params = workflow1.properties["parameters"]
        print("Final workflow variables: %s" % params)
        self.assertEqual("789", params["COUNTER"])
        self.assertEqual(2, len(workflow1.get_files()))
        self.assertEqual(2, len(workflow1.get_jobs()))
        print("Output from date1: %s " % workflow1.stat("wf:date1/stdout").raw().read())
        print("Output from date2: %s " % workflow1.stat("wf:date2/stdout").raw().read())


if __name__ == "__main__":
    unittest.main()
