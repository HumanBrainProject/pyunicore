import dataclasses
from typing import Dict
from typing import Tuple
from typing import Union
from typing import Any
from typing import Type as PythonType

from pyunicore.helpers import _api_object


class Type:
    """Accepted variable types for workflow variables."""

    String = str
    Integer = int
    Float = float
    Boolean = bool

    @classmethod
    def get_types(cls) -> Tuple[PythonType]:
        """Return all available types."""
        return tuple(cls._types().keys())

    @classmethod
    def get_type_name(cls, type: PythonType) -> str:
        """Get the UNICORE name for the type."""
        return cls._types()[type]

    @classmethod
    def _types(cls) -> Dict[PythonType, str]:
        return {
            cls.String: "STRING",
            cls.Integer: "INTEGER",
            cls.Float: "FLOAT",
            cls.Boolean: "BOOLEAN",
        }


@dataclasses.dataclass
class Variable(_api_object.ApiRequestObject):
    """UNICORE's variable description for submitting workflows.

    Args:
        name (str): Name of the variable.
        type (Type): Type of the variable.
        initial_value: Initial value of the variable.

    """

    name: str
    type: Union[Type, Any]
    initial_value: Any

    def __post_init__(self) -> None:
        self._check_for_correct_type()
        self._check_initial_value_for_correct_type()

    def _check_for_correct_type(self):
        allowed_types = Type.get_types()
        if self.type not in allowed_types:
            raise ValueError(
                f"{self.type} is not a valid variable type. "
                f"Allowed variable types: {allowed_types}"
            )

    def _check_initial_value_for_correct_type(self) -> None:
        if not isinstance(self.initial_value, self.type):
            actual_type = type(self.initial_value)
            raise ValueError(
                f"Initial value of {self} has incorrect type "
                f"{actual_type}, expected {self.type}"
            )

    def _to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": Type.get_type_name(self.type),
            "initial_value": self._convert_value(),
        }

    def _convert_value(self) -> Any:
        if self.type == Type.Boolean:
            return str(self.initial_value).lower()
        return self.initial_value
