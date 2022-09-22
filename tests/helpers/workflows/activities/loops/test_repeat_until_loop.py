from pyunicore.helpers.workflows.activities import loops
from pyunicore.helpers.workflows import variable

class TestRepeatUntil:
    def test_to_dict(self, loop_body, expected_loop_body):
        variables = [variable.Variable(name="test-variable", type=variable.VariableType.Integer, initial_value=1)]
        loop = loops.RepeatUntil(
            id="test-repeat-until-loop-id",
            variables=variables,
            body=loop_body,
        )

        expected = {
            "id": "test-repeat-until-loop-id",
            "type": "REPEAT_UNTIL",
            "variables": [{"name": "test-variable", "type": "INTEGER", "initial_value": 1}],
            "body": expected_loop_body,
        }

        result = loop.to_dict()

        assert result == expected