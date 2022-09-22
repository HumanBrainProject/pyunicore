import dataclasses
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pyunicore.helpers import _api_object
from pyunicore.helpers.workflows import variable
from pyunicore.helpers.workflows.activities.loops import _loop


@dataclasses.dataclass
class Values(_api_object.ApiRequestObject):
    values: List

    def _to_dict(self) -> Dict:
        return {"values": self.values}


@dataclasses.dataclass
class Variable(variable.Variable):
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
class Variables(_api_object.ApiRequestObject):
    variables: List[Variable]

    def _to_dict(self) -> Dict:
        return {"variables": self.variables}


@dataclasses.dataclass
class File(_api_object.ApiRequestObject):
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
class Files(_api_object.ApiRequestObject):
    files: List[File]

    def _to_dict(self) -> Dict:
        return {"file_sets": self.files}


@dataclasses.dataclass
class Chunking(_api_object.ApiRequestObject):
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
class ForEach(_loop.Loop):
    """A for-each-loop-like activity within a workflow.

    Args:
        job (JobDescription): Description of the job.
        site_name (str): Name of the site to execute the job on.
        user_preferences (UserPreferences, optional): User preferences to pass.
        options (list[JobOption], optional): Options to pass.

    """

    iterator_name: str
    range: Union[Values, Variables, Files]
    chunking: Optional[Chunking]

    def _type(self) -> str:
        return "FOR_EACH"

    def _activity_to_dict(self) -> Dict:
        return {
            "iterator_name": self.iterator_name,
            "body": self.body,
            **self.range,
        }
