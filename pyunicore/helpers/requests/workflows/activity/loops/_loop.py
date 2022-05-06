import dataclasses

from pyunicore.helpers.requests.workflows.activity import activity
from . import body


@dataclasses.dataclass
class Loop(activity.Activity):
    """A loop-like activity within a workflow."""

    body: body.Body
