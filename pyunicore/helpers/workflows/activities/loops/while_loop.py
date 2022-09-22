import dataclasses
from typing import Dict
from typing import List

from pyunicore.helpers.workflows import variable
from pyunicore.helpers.workflows.activities.loops import _loop


@dataclasses.dataclass
class While(_loop.Loop):
    """A while-loop-like activity within a workflow.

    Args:
        variables (list[Variable]): Variables to use in the loop.

    """

    variables: List[variable.Variable]

    def _type(self) -> str:
        return "WHILE"

    def _activity_to_dict(self) -> Dict:
        return {
            "variables": self.variables,
            "body": self.body,
        }
