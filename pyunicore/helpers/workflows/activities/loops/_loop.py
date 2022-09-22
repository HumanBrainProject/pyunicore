import dataclasses

from pyunicore.helpers.workflows.activities import activity
from pyunicore.helpers.workflows.activities.loops import body


@dataclasses.dataclass
class Loop(activity.Activity):
    """A loop-like activity within a workflow.

    Args:
        body (Body): Loop body.

    """

    body: body.Body
