import dataclasses
from typing import Dict

import pytest

import pyunicore.helpers._api_object as api_object


@dataclasses.dataclass
class ApiObject(api_object.ApiRequestObject):
    test: str = "test"

    def _to_dict(self) -> Dict:
        return dataclasses.asdict(self)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {"any": "value"},
            {"any": "value"},
        ),
        (
            {"any": None},
            {},
        ),
        (
            {"any": ApiObject()},
            {"any": {"test": "test"}},
        ),
        # bool needs to be converted to lower-case string
        (
            {"any": True},
            {"any": "true"},
        ),
        (
            {"any": False},
            {"any": "false"},
        ),
    ],
)
def test_create_dict_with_not_none_values(kwargs, expected):
    result = api_object._create_dict_with_not_none_values(kwargs)

    assert result == expected
