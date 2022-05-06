import pyunicore.helpers.workflows as workflows


class TestWorkflowDescription:
    def test_to_dict(self):
        activities = [workflows.activities.Start(id="test-start")]
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

        workflow = workflows.Description(
            activities=activities,
            transitions=transitions,
            variables=variables,
        )
        expected = {
            "activities": [{"id": "test-start", "type": "START"}],
            "transitions": [{"from": "here", "to": "there"}],
            "variables": [
                {"initial_value": 1, "name": "test-variable", "type": "INTEGER"}
            ],
        }

        result = workflow.to_dict()

        breakpoint()
        assert result == expected
