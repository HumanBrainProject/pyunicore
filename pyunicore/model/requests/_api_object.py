import abc
from typing import Dict


class ApiRequestObject(abc.ABC):
    """Any object for API requests."""

    @abc.abstractmethod
    def to_dict(self) -> Dict:
        """Return as dict."""
