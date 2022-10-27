import dataclasses
from typing import Dict
from typing import Optional

from pyunicore.helpers import _api_object


@dataclasses.dataclass
class Credentials(_api_object.ApiRequestObject):
    """Credentials for an external service a file might be imported from.

    Args:
        username (str): User name.
        password (str): Password.

    """

    username: str
    password: str

    def _to_dict(self) -> Dict[str, str]:
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
    data: Optional[str] = None
    credentials: Optional[Credentials] = None

    def _to_dict(self) -> Dict:
        return {
            "From": self.from_,
            "To": self.to,
            "FailOnError": self.fail_on_error,
            "Data": self.data,
            "Credentials": self.credentials,
        }


@dataclasses.dataclass
class Export(_api_object.ApiRequestObject):
    """An export."""

    from_: str
    to: str

    def _to_dict(self) -> Dict[str, str]:
        return {
            "From": self.from_,
            "To": self.to,
        }
