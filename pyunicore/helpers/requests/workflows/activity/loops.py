import dataclasses
from typing import Dict
from typing import List
from typing import Optional

from pyunicore.helpers.requests import _api_object
from pyunicore.helpers.requests.workflows import variable
from pyunicore.helpers.requests.workflows import transition
from . import activity


@dataclasses.dataclass
class _LoopBody(_api_object.ApiRequestObject):
    """Body of a while loop."""

    activities: List[activity.Activity]
    transitions: List[transition.Transition]
    condition: str

    def _to_dict(self) -> Dict:
        return {
            "activities": self.activities,
            "transitions": self.transitions,
            "condition": self.condition,
        }


@dataclasses.dataclass
class WhileLoop(activity.Activity):
    """A while-loop-like activity within a workflow.

    Args:
        job (JobDescription): Description of the job.
        site_name (str): Name of the site to execute the job on.
        user_preferences (UserPreferences, optional): User preferences to pass.
        options (list[JobOption], optional): Options to pass.

    """

    class Body(_LoopBody):
        """Body of a while loop."""

    variables: List[variable.Variable]
    body: Body

    def _type(self) -> str:
        return "WHILE"

    def _activity_to_dict(self) -> Dict:
        return {
            "variables": self.variables,
            "body": self.body,
        }


@dataclasses.dataclass
class RepeatUntilLoop(WhileLoop):
    """A repeat-until-loop-like activity within a workflow."""

    def _type(self) -> str:
        return "REPEAT_UNTIL"


@dataclasses.dataclass
class _ForEachValues(_api_object.ApiRequestObject):
    values: List

    def _to_dict(self) -> Dict:
        return {"values": self.values}


@dataclasses.dataclass
class _ForEachVariable(variable.Variable):
    expression: str
    end_condition: str

    def _to_dict(self) -> Dict:
        return {
            "variable_name": self.name,
            "type": self.Type.get_type_name(self.type),
            "start_value": self.initial_value,
            "expression": self.expression,
            "end_condition": self.end_condition,
        }


@dataclasses.dataclass
class _ForEachVariables(_api_object.ApiRequestObject):
    variables: List[_ForEachVariable]

    def _to_dict(self) -> Dict:
        return {"variables": self.variables}


@dataclasses.dataclass
class _ForEachFile(_api_object.ApiRequestObject):
    base: str
    include: List[str]
    exclude: List[str]
    recurse: bool
    indirection: bool

    def _to_dict(self) -> Dict:
        return {
            "base": self.base,
            "include": self.include,
            "exclude": self.exclude,
            "recurse": self.recurse,
            "indirection": self.indirection,
        }


@dataclasses.dataclass
class _ForEachFiles(_api_object.ApiRequestObject):
    files: List[_ForEachFile]

    def _to_dict(self) -> Dict:
        return {"file_sets": self.files}


@dataclasses.dataclass
class _ForEachChunking(_api_object.ApiRequestObject):
    class Type:
        """The type of the chunks.

        Attrs:
            Normal (str): Number of files to use as chunks.
            Size (str): Size in kbytes to process per chunk.

        """

        Normal = "NORMAL"
        Size = "SIZE"

    chunksize: int
    type: Type
    filename_format: str
    chunksize_formula: str

    def _to_dict(self) -> Dict:
        return {
            "chunksize": self.chunksize,
            "type": self.type,
            "filename_format": self.filename_format,
            "chunksize_formula": self.chunksize_formula,
        }


@dataclasses.dataclass
class ForEachLoop(activity.Activity):
    """A for-each-loop-like activity within a workflow.

    Args:
        job (JobDescription): Description of the job.
        site_name (str): Name of the site to execute the job on.
        user_preferences (UserPreferences, optional): User preferences to pass.
        options (list[JobOption], optional): Options to pass.

    """

    class Body(_LoopBody):
        """Body of a for loop."""

    class Range:
        """Range to loop over."""

        class Values(_ForEachValues):
            """A range of values to loop over."""

        class Variables(_ForEachVariables):
            """A range of variables to loop over."""

            class Variable(_ForEachVariable):
                """A variable."""

        class Files(_ForEachFiles):
            """A range of files to loop over."""

            class File(_ForEachFile):
                """A file."""

    class Chunking(_ForEachChunking):
        """The chunking of the data."""

    iterator_name: str
    body: Body
    range: Range
    chunking: Optional[Chunking]

    def _type(self) -> str:
        return "FOR_EACH"

    def _activity_to_dict(self) -> Dict:
        return {
            "iterator_name": self.iterator_name,
            "body": self.body,
            **self.range,
        }
