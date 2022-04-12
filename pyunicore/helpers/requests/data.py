from typing import Dict

import dataclasses

from . import _api_object
from . import _dict_helper


@dataclasses.dataclass
class Credentials(_api_object.ApiRequestObject):
    """Credentials for an external service a file might be imported from.

    Args:
        username (str): User name.
        password (str): Password.

    """

    username: str
    password: str

    def to_dict(self) -> Dict[str, str]:
        """Return as dict."""
        return {
            "Username": self.username,
            "Password": self.password,
        }


@dataclasses.dataclass
class Import(_api_object.ApiRequestObject):
    """An import."""

    from_: str
    to: str
    fail_on_error: bool = True
    data: str = None
    credentials: Credentials = None

    def to_dict(self) -> Dict:
        """Return as dict."""
        key_values = {
            "From": self.from_,
            "To": self.to,
            "FailOnError": self.fail_on_error,
            "Data": self.data,
            "Credentials": self.credentials,
        }
        return _dict_helper.create_dict_with_not_none_values(**key_values)


@dataclasses.dataclass
class Export(_api_object.ApiRequestObject):
    """An export."""

    from_: str
    to: str

    def to_dict(self) -> Dict[str, str]:
        """Return as dict."""
        return {
            "From": self.from_,
            "To": self.to,
        }
