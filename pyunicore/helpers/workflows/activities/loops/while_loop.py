import dataclasses
from typing import Dict
from typing import List

from pyunicore.helpers.workflows import variable
from pyunicore.helpers.workflows.activities.loops import _loop


@dataclasses.dataclass
class While(_loop.Loop):
    """A while-loop-like activity within a workflow.

    Args:
        job (JobDescription): Description of the job.
        site_name (str): Name of the site to execute the job on.
        user_preferences (UserPreferences, optional): User preferences to pass.
        options (list[JobOption], optional): Options to pass.

    """

    variables: List[variable.Variable]

    def _type(self) -> str:
        return "WHILE"

    def _activity_to_dict(self) -> Dict:
        return {
            "variables": self.variables,
            "body": self.body,
        }
