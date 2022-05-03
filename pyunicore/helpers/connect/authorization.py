import abc
import dataclasses


class Authorization(abc.ABC):
    """Represents an HTTP authorization method."""

    def __str__(self) -> str:
        """Mask credentials when formatted as string."""
        return self.__repr__()

    def __repr__(self) -> str:
        """Mask credentials when printed."""
        return f"{self.__class__.__name__}(<masked>)"


@dataclasses.dataclass(repr=False)
class UserAuthorization(Authorization):
    """Authorization  with user and password.

    Args:
        user (str): JUDOOR user name.
        password (str): Corresponding JUDOOR user password.

    """

    user: str
    password: str


@dataclasses.dataclass(repr=False)
class TokenAuthorization(Authorization):
    """Authorization with a bearer token.

    Args:
        token (str): The bearer token.

    """

    token: str
