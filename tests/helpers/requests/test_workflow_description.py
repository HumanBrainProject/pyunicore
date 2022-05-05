import pyunicore.helpers.requests.workflow_description as workflow_description


class TestWorkflowDescription:
    def test_to_dict(self):
        workflow = workflow_description.WorkflowDescription()
        expected = {}

        result = workflow.to_dict()

        assert result == expected
