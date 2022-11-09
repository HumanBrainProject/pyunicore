import dataclasses
from typing import Dict
from typing import Optional

from pyunicore.helpers import _api_object


@dataclasses.dataclass
class Transition(_api_object.ApiRequestObject):
    """UNICORE's transition description for submitting workflows.

    Args:
        from_ (str): ID of the activity or subworkflow.
        to (str): ID of the activity or subworkflow.
        condition (str, optional): Transition is only followed if this
            evaluates to true.

    """

    from_: str
    to: str
    condition: Optional[str] = None

    def _to_dict(self) -> Dict:
        return {
            "from": self.from_,
            "to": self.to,
            "condition": self.condition,
        }
