import abc
from typing import Any
from typing import Dict
from typing import List
from typing import Union


class ApiRequestObject(abc.ABC):
    """Any object for API requests."""

    def to_dict(self) -> Dict:
        """Return as dict."""
        as_dict = self._to_dict()
        return _create_dict_with_not_none_values(as_dict)

    @abc.abstractmethod
    def _to_dict(self) -> Dict:
        """Return as dict."""


def _create_dict_with_not_none_values(kwargs: Dict) -> Dict:
    return {key: _convert_value(value) for key, value in kwargs.items() if value is not None}


def _convert_value(value: Union[Any, ApiRequestObject]) -> Any:
    if isinstance(value, dict):
        return _create_dict_with_not_none_values(value)
    elif isinstance(value, (list, tuple, set)):
        return _create_list_with_not_none_values(value)
    elif isinstance(value, ApiRequestObject):
        return value.to_dict()
    elif isinstance(value, bool):
        return str(value).lower()
    return value


def _create_list_with_not_none_values(values: List) -> List:
    return [_convert_value(value) for value in values if value is not None]
