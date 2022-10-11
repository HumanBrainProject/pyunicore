import abc
import dataclasses
from typing import Dict

from pyunicore.helpers import _api_object


@dataclasses.dataclass
class Activity(_api_object.ApiRequestObject):
    """UNICORE's activity description for submitting workflows.

    Args:
        id (str): ID of the activity.
            Must be unique within the workflow.

    """

    id: str

    @property
    def type(self) -> str:
        """Return the UNICORE type of the activity."""
        return self._type()

    @abc.abstractmethod
    def _type(self) -> str:
        """Return the UNICORE type of the activity."""

    def _to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            **self._activity_to_dict(),
        }

    @abc.abstractmethod
    def _activity_to_dict(self) -> Dict:
        """Return dict for the respective activity type."""


@dataclasses.dataclass
class Start(Activity):
    """A start activity within a workflow.

    Denotes an explicit start activity. If no such activity is present, the
    processing engine will try to detect the proper starting activities.

    """

    def _type(self) -> str:
        return "START"

    def _activity_to_dict(self) -> Dict:
        return {}


@dataclasses.dataclass
class Split(Activity):
    """A split activity within a workflow.

    This activity can have multiple outgoing transitions. All transitions with
    matching conditions will be followed. This is comparable to an
    "if() … if() … if()" construct in a programming language.

    """

    def _type(self) -> str:
        return "Split"

    def _activity_to_dict(self) -> Dict:
        return {}


@dataclasses.dataclass
class Branch(Activity):
    """A start activity within a workflow.

    This activity can have multiple outgoing transitions. The transition with
    the first matching condition will be followed. This is comparable to an
    "if() … elseif() … else()" construct in a programming language.

    """

    def _type(self) -> str:
        return "BRANCH"

    def _activity_to_dict(self) -> Dict:
        return {}


@dataclasses.dataclass
class Merge(Activity):
    """A start activity within a workflow.

    Denotes an explicit start activity. If no such activity is present, the
    processing engine will try to detect the proper starting activities.

    """

    def _type(self) -> str:
        return "Merge"

    def _activity_to_dict(self) -> Dict:
        return {}


@dataclasses.dataclass
class Synchronize(Activity):
    """A start activity within a workflow.

    Merges multiple flows and synchronises them.

    """

    def _type(self) -> str:
        return "Synchronize"

    def _activity_to_dict(self) -> Dict:
        return {}


@dataclasses.dataclass
class Hold(Activity):
    """A hold activity within a workflow.

    Stops further processing of the current flow until the client explicitely
    sends continue message.

    """

    def _type(self) -> str:
        return "HOLD"

    def _activity_to_dict(self) -> Dict:
        return {}
