"""Represents the job description of the UNICORE REST API.

See https://unicore-dev.zam.kfa-juelich.de/documentation/workflow-8.0.0/workflow-manual.html  # noqa

"""
import dataclasses
from typing import Dict

from . import _api_object


@dataclasses.dataclass
class WorkflowDescription(_api_object.ApiRequestObject):
    """UNICORE's workflow description for submitting workflows."""

    def _to_dict(self) -> Dict:
        return {}
