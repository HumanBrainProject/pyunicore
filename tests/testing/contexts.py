import contextlib
from typing import Any

import pytest  # type: ignore


def expect_raise_if_exception(
    expected: Any,
):
    """Create a context that expects a raised exception or no raised exception.

    Args:
        expected: The expected result.

    Returns:
        _pytest.python_api.RaisesContext: If expected is of type `Exception`
        contextlib.suppress: otherwise.

    """
    return (
        pytest.raises(type(expected)) if isinstance(expected, Exception) else contextlib.suppress()
    )
