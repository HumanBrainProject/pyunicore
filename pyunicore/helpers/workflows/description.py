import dataclasses
from typing import Dict
from typing import List
from typing import Optional

from pyunicore.helpers import _api_object
from pyunicore.helpers.workflows import transition
from pyunicore.helpers.workflows import variable
from pyunicore.helpers.workflows.activities import activity


@dataclasses.dataclass
class Description(_api_object.ApiRequestObject):
    """UNICORE's workflow description for submitting workflows.

    Args:
        activities (list):
        subworkflows (list(Description), optional):
        transitions (list):
        variables (list):
        notification (str, optional): URL to send notifications to.
            The UNICORE Workflow server will send a POST notification when the
            workflow has finished processing. Notifcation messages have the
            following content:
            ```JSON
            {
              "href" : "workflow_url",
              "group_id": "id of the workflow or sub-workflow",
              "status": "...",
              "statusMessage": "..."
            }
            ```
        tags (list, optional): tags for filtering the list of workflows.

    """

    activities: List[activity.Activity]
    transitions: List[transition.Transition]
    variables: List[variable.Variable]
    subworkflows: Optional[List["Description"]] = None
    notification: Optional[str] = None
    tags: Optional[List[str]] = None

    def _to_dict(self) -> Dict:
        return {
            "activities": self.activities,
            "subworkflows": self.subworkflows,
            "transitions": self.transitions,
            "variables": self.variables,
            "notification": self.notification,
            "tags": self.tags,
        }
