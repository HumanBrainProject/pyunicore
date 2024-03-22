import pytest

from pyunicore.helpers.workflows import variable
from tests import testing


class TestVariable:
    @pytest.mark.parametrize(
        ("type", "initial_value", "expected"),
        [
            (
                variable.VariableType.Integer,
                1,
                {
                    "name": "test-variable",
                    "type": "INTEGER",
                    "initial_value": 1,
                },
            ),
            (
                variable.VariableType.String,
                "test",
                {
                    "name": "test-variable",
                    "type": "STRING",
                    "initial_value": "test",
                },
            ),
            (
                variable.VariableType.Float,
                1.0,
                {
                    "name": "test-variable",
                    "type": "FLOAT",
                    "initial_value": 1.0,
                },
            ),
            (
                variable.VariableType.Boolean,
                True,
                {
                    "name": "test-variable",
                    "type": "BOOLEAN",
                    "initial_value": "true",
                },
            ),
            (
                variable.VariableType.Boolean,
                False,
                {
                    "name": "test-variable",
                    "type": "BOOLEAN",
                    "initial_value": "false",
                },
            ),
            # Test case: Given type not supported.
            (
                dict,
                {},
                ValueError(),
            ),
            # Test case: Initial value not of correct type.
            (
                variable.VariableType.Float,
                "wrong type",
                ValueError(),
            ),
        ],
    )
    def test_to_dict(self, type, initial_value, expected):
        with testing.expect_raise_if_exception(expected):
            var = variable.Variable(
                name="test-variable",
                type=type,
                initial_value=initial_value,
            )

            assert var.to_dict() == expected
