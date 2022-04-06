from typing import Dict


def create_dict_with_not_none_values(**kwargs) -> Dict:
    return {
        key: value
        for key, value in kwargs.items()
        if value is not None
    }

