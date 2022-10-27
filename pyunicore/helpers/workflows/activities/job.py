import abc
import dataclasses
from typing import Dict
from typing import List
from typing import Optional
from typing import Type

from pyunicore.helpers import _api_object
from pyunicore.helpers import jobs
from pyunicore.helpers.workflows.activities import activity


class Option:
    """An activity option for jobs in a workflow."""

    class _Option(_api_object.ApiRequestObject):
        value: Type

        def _to_dict(self) -> Dict:
            return {self._name: self.value}

        @property
        @abc.abstractmethod
        def _name(self) -> str:
            """Return the UNICORE name of the option."""

    @dataclasses.dataclass
    class IgnoreFailure(_Option):
        """Whether to ignore any failure of the task.

        Args:
            value (bool): Whether to ignore the failure.
                The workflow engine continues processing as if the activity had
                been completed successfully. This has nothing to do with the
                exit code of the actual UNICORE job! Failure means for example
                data staging failed, or no matching target system for the job
                could be found.

        """

        value: bool

        @property
        def _name(self) -> str:
            return "IGNORE_FAILURE"

    @dataclasses.dataclass
    class MaxResubmits(_Option):
        """Number of times the activity will be retried.

        By default, the workflow engine will re-try three times.

        """

        value: int

        @property
        def _name(self) -> str:
            return "MAX_RESUBMITS"


@dataclasses.dataclass
class UserPreferences(_api_object.ApiRequestObject):
    """User preferences."""

    role: str
    uid: str
    group: str
    supplementary_groups: str

    def _to_dict(self) -> dict:
        return {
            "role": self.role,
            "uid": self.uid,
            "group": self.group,
            "supplementaryGroups": self.supplementary_groups,
        }


@dataclasses.dataclass
class Job(activity.Activity):
    """A job activity within a workflow.

    Denotes a executable (job) activity. In this case, the job sub element
    holds the JSON job definition. (If a "job" element is present, you may
    leave out the "type".)

    Args:
        job (JobDescription): Description of the job.
        site_name (str): Name of the site to execute the job on.
        user_preferences (UserPreferences, optional): User preferences to pass.
        options (list[JobOption], optional): Options to pass.

    """

    description: jobs.Description
    site_name: str
    user_preferences: Optional[UserPreferences] = None
    options: Optional[List[Option]] = None

    def _type(self) -> str:
        return "JOB"

    def _activity_to_dict(self) -> Dict:
        if self.options is not None:
            options = {k: v for o in self.options for k, v in o.to_dict().items()}
        else:
            options = None

        return {
            "job": {
                **self.description.to_dict(),
                "Site name": self.site_name,
                "User preferences": self.user_preferences,
            },
            "options": options,
        }
