import pytest

from pyunicore.helpers.workflows import variable
from pyunicore import testing


class TestVariable:
    @pytest.mark.parametrize(
        ("type", "initial_value", "expected"),
        [
            #(variable.Type.Integer, 1, {"name": "test-variable", "type": "INTEGER", "initial_value": 1}),
            (variable.Type.String, "test", {"name": "test-variable", "type": "STRING", "initial_value": "test"}),
            (variable.Type.Float, 1.0, {"name": "test-variable", "type": "FLOAT", "initial_value": 1.0}),
            (variable.Type.Boolean, True, {"name": "test-variable", "type": "BOOLEAN", "initial_value": "true"}),
            (variable.Type.Boolean, False, {"name": "test-variable", "type": "BOOLEAN", "initial_value": "false"}),
        ]
    )
    def test_init(self, type, initial_value, expected):
        with testing.expect_raise_if_exception(expected):
            var = variable.Variable(
                name="test-variable",
                type=type,
                initial_value=initial_value,
            )

            assert var.to_dict() == expected
