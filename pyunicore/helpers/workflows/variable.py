import dataclasses
from typing import Dict
from typing import Tuple
from typing import Type as tType

from pyunicore.helpers import _api_object


class _VariableType:
    """Accepted variable types for workflow variables."""

    String = str
    Integer = int
    Float = float
    Boolean = bool

    @classmethod
    def get_types(cls) -> Tuple[tType]:
        """Return all available types."""
        return tuple(cls._types().keys())

    @classmethod
    def get_type_name(cls, type: tType) -> str:
        """Get the UNICORE name for the type."""
        return cls._types()[type]

    @classmethod
    def _types(cls) -> Dict[tType, str]:
        return {
            str: "STRING",
            int: "INTEGER",
            float: "FLOAT",
            bool: "BOOLEAN",
        }


@dataclasses.dataclass
class Variable(_api_object.ApiRequestObject):
    """UNICORE's variable description for submitting workflows.

    Args:
        name (str): Name of the variable.
        type (VariableType): Type of the variable.
        initial_value: Initial value of the variable.

    """

    class Type(_VariableType):
        """Accepted variable types for workflow variables."""

    name: str
    type: Type
    initial_value: tType

    def __post_init__(self) -> None:
        self._check_for_correct_type()
        self._check_initial_value_for_correct_type()

    def _check_for_correct_type(self):
        allowed_types = self.Type.get_types()
        if self.type not in allowed_types:
            raise ValueError(
                f"{self.type} is not a valid variable type. "
                f"Allowed variable types: {allowed_types}"
            )

    def _check_initial_value_for_correct_type(self) -> None:
        if not isinstance(self.initial_value, self.type):
            actual_type = type(self.initial_value)
            raise ValueError(
                f"Initial value of {self._instance_name} has incorrect type "
                f"{actual_type}, expected {self.type}"
            )

    @property
    def _instance_name(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"

    def _to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.Type.get_type_name(self.type),
            "initial_value": self.initial_value,
        }
