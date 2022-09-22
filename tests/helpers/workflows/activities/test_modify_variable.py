from pyunicore.helpers.workflows.activities import modify_variable


class TestModifyVariable:
    def test_to_dict(self):
        variable = modify_variable.ModifyVariable(
            id="test-id", variable_name="x", expression="x + 1"
        )
        expected = {
            "id": "test-id",
            "type": "ModifyVariable",
            "variableName": "x",
            "expression": "x + 1",
        }

        result = variable.to_dict()

        assert result == expected
