import abc
from typing import Dict


class ApiRequestObject(abc.ABC):
    """Any object for API requests."""

    def to_dict(self) -> Dict:
        """Return as dict."""
        return self._to_dict()

    @abc.abstractmethod
    def _to_dict(self) -> Dict:
        ...
