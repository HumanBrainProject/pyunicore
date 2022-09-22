from pyunicore.helpers.workflows.activities import loops
from pyunicore.helpers.workflows import variable

class TestWhileLoop:
    def test_to_dict(self, loop_body, expected_loop_body):
        variables = [variable.Variable(name="test-variable", type=variable.VariableType.Integer, initial_value=1)]
        loop = loops.While(
            id="test-while-loop-id",
            variables=variables,
            body=loop_body,
        )

        expected = {
            "id": "test-while-loop-id",
            "type": "WHILE",
            "variables": [{"name": "test-variable", "type": "INTEGER", "initial_value": 1}],
            "body": expected_loop_body,
        }

        result = loop.to_dict()

        assert result == expected