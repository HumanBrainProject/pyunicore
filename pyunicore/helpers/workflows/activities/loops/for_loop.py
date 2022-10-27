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
    """A range of values to iterate over."""

    values: List

    def _to_dict(self) -> Dict:
        return {"values": self.values}


@dataclasses.dataclass
class Variable(variable.Variable):
    """A variable to use in an iteration.

    Args:
        expression (str): Expression to evaluate at each iteration.
        end_condition (str): Condition when to end the iteration.

    """

    expression: str
    end_condition: str

    def _to_dict(self) -> Dict:
        return {
            "variable_name": self.name,
            "type": variable.VariableType.get_type_name(self.type),
            "start_value": self.initial_value,
            "expression": self.expression,
            "end_condition": self.end_condition,
        }


@dataclasses.dataclass
class Variables(_api_object.ApiRequestObject):
    """A set of variables to iterate over."""

    variables: List[Variable]

    def _to_dict(self) -> Dict:
        return {"variables": self.variables}


@dataclasses.dataclass
class File(_api_object.ApiRequestObject):
    """A file configuration to include in an iteration.

    Args:
        base (str): Base of the filenames, which will be resolved at runtime.
        include (list[str]): List if file names or regular expressions.
        exclude (list[str]): List if file names or regular expressions.
        recurse (bool, default=False): Whether the resolution should be done
            recursively into any subdirectories.
        indirection (bool, default=False): Whether to load the given file(s)
            at runtime.


    """

    base: str
    include: List[str]
    exclude: List[str]
    recurse: bool = False
    indirection: bool = False

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
    """A set of files to iterator over."""

    files: List[File]

    def _to_dict(self) -> Dict:
        return {"file_sets": self.files}


class ChunkingType:
    """The type of the chunks.

    Attrs:
        Normal (str): Number of files to use as chunks.
        Size (str): Size in kbytes to process per chunk.

    """

    Normal = "NORMAL"
    Size = "SIZE"


@dataclasses.dataclass
class Chunking(_api_object.ApiRequestObject):
    """A chunking configuration to use in an iteration.

    Args:
        chunksize(int): Size of the chunks.
        chunksize_formula (str, optional): Expression to use to calculate the
            chunksize at runtime.
        type (ChunkingType, default=Normal): Type of the `chunksize`.
            - `ChunkingType.Normal`: Number of files in a chunk.
            - `ChunkingType.Size`: Total size of a chunk in kbytes.
        filename_format (str): Allows to control how the individual files
            should be named.

    Notes:
        Either `chunksize` or `chunksize_formula` must be given.

    """

    chunksize: Optional[int] = None
    chunksize_formula: Optional[str] = None
    type: ChunkingType = ChunkingType.Normal
    filename_format: Optional[str] = None

    def __post_init__(self):
        """Check that either chunksize or formula is given."""
        if (self.chunksize is None and self.chunksize_formula is None) or (
            self.chunksize is not None and self.chunksize_formula is not None
        ):
            raise ValueError("Either `chunksize` or `chunksize_formula` must be given")

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
        range (Values, Variables or Files): Range to iterator over.
        iterator_name (str, default="IT"): Name of the iterator.
        chunking (Chunking): Chunking to use for the range.

    """

    range: Union[Values, Variables, Files]
    iterator_name: str = "IT"
    chunking: Optional[Chunking] = None

    def _type(self) -> str:
        return "FOR_EACH"

    def _activity_to_dict(self) -> Dict:
        return {
            "iterator_name": self.iterator_name,
            "body": self.body,
            "chunking": self.chunking,
            **self.range.to_dict(),
        }
