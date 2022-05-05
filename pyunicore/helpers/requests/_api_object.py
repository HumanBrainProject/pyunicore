import abc
from typing import Any
from typing import Dict
from typing import Union


class ApiRequestObject(abc.ABC):
    """Any object for API requests."""

    def to_dict(self) -> Dict:
        """Return as dict."""
        as_dict = self._to_dict()
        return _create_dict_with_not_none_values(as_dict)

    @abc.abstractmethod
    def _to_dict(self) -> Dict:
        ...


def _create_dict_with_not_none_values(kwargs) -> Dict:
    return {
        key: _convert_value(value)
        for key, value in kwargs.items()
        if value is not None
    }


def _convert_value(value: Union[Any, ApiRequestObject]) -> Any:
    if isinstance(value, ApiRequestObject):
        return value.to_dict()
    elif isinstance(value, bool):
        return str(value).lower()
    return value
