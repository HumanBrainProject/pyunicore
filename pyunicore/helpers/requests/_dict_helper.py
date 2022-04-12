from typing import Any
from typing import Dict
from typing import Union

from . import _api_object


def create_dict_with_not_none_values(**kwargs) -> Dict:
    return {
        key: _convert_value(value)
        for key, value in kwargs.items()
        if value is not None
    }


def _convert_value(value: Union[Any, _api_object.ApiRequestObject]) -> Any:
    if isinstance(value, _api_object.ApiRequestObject):
        return value.to_dict()
    elif isinstance(value, bool):
        return str(value).lower()
    return value
