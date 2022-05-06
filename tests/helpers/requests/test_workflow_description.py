import pyunicore.helpers.requests.workflows as workflows


class TestWorkflowDescription:
    def test_to_dict(self):
        activities = [workflows.Activity.Start]
        transitions = [
            workflows.Transition(
                from_="here",
                to="there",
            )
        ]
        variables = [
            workflows.Variable(
                name="test-variable",
                type=workflows.Variable.Type.Integer,
                initial_value=1,
            )
        ]

        workflow = workflows.WorkflowDescription(
            activities=activities,
            transitions=transitions,
            variables=variables,
        )
        expected = {}

        result = workflow.to_dict()

        assert result == expected
