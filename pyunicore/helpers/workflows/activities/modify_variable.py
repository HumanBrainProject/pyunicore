import dataclasses
from typing import Dict

from pyunicore.helpers.workflows.activities import activity


@dataclasses.dataclass
class ModifyVariable(activity.Activity):
    """Modifies a variable within the workflow.

    Allows to modify a workflow variable. An option named "variableName"
    identifies the variable to be modified, and an option "expression" holds
    the modification expression in the Groovy programming language syntax.

    Args:
        variable_name (str): name of the variable to modify.
        expression (str): Groovy-syntax expression to modify the variable.

    """

    variable_name: str
    expression: str

    def _type(self) -> str:
        return "ModifyVariable"

    def _activity_to_dict(self) -> Dict:
        return {
            "variableName": self.variable_name,
            "expression": self.expression,
        }
