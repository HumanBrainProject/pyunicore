import abc
import dataclasses


class Authentication(abc.ABC):
    """Represents an HTTP authentication method."""

    def __str__(self) -> str:
        """Mask credentials when formatted as string."""
        return self.__repr__()

    def __repr__(self) -> str:
        """Mask credentials when printed."""
        return f"{self.__class__.__name__}(<masked>)"


@dataclasses.dataclass(repr=False)
class UserAuthentication(Authentication):
    """Authentication  with user and password.

    Args:
        user (str): JUDOOR user name.
        password (str): Corresponding JUDOOR user password.

    """

    user: str
    password: str


@dataclasses.dataclass(repr=False)
class TokenAuthentication(Authentication):
    """Authentication with a bearer token.

    Args:
        token (str): The bearer token.

    """

    token: str
