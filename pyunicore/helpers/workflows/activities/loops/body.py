import dataclasses
from typing import Dict
from typing import List

from pyunicore.helpers import _api_object
from pyunicore.helpers.workflows import transition
from pyunicore.helpers.workflows.activities import activity


@dataclasses.dataclass
class Body(_api_object.ApiRequestObject):
    """Body of a loop."""

    activities: List[activity.Activity]
    transitions: List[transition.Transition]
    condition: str

    def _to_dict(self) -> Dict:
        return {
            "activities": self.activities,
            "transitions": self.transitions,
            "condition": self.condition,
        }
