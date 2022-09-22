from typing import Dict

import pytest

from pyunicore.helpers.workflows.activities import loops
from pyunicore.helpers.workflows import activities as _activities
from pyunicore.helpers.workflows import transition


@pytest.fixture(scope="session")
def loop_body() -> loops.Body:
    activities = [
        _activities.ModifyVariable(
            id="test-modify-variable-id",
            variable_name="test-variable",
            expression="test-expression",
        )
    ]
    transitions = [
        transition.Transition(
            from_="here", to="there", condition="test-condition"
        )
    ]
    return loops.Body(
        activities=activities,
        transitions=transitions,
        condition="test-body-condition",
    )


@pytest.fixture(scope="session")
def expected_loop_body() -> Dict:
    return {
        "activities": [
            {
                "id": "test-modify-variable-id",
                "type": "ModifyVariable",
                "variableName": "test-variable",
                "expression": "test-expression",
            },
        ],
        "transitions": [
            {"from": "here", "to": "there", "condition": "test-condition"},
        ],
        "condition": "test-body-condition",
    }
