from typing import Callable


_ID_FILTER = Callable[[tuple[str, list[str]]], bool]
"""Defines a type for a high-order function.

Use when defining a high-order function that accepts a two-tuple of `str`
and `list[str]`. These will often be used for filtering entries in the
measure versions `dict` of the Home model.
"""


_VERSION_FILTER = Callable[[str], bool]
"""Defines a type for a high-order function.

Use when defining a high-order function that accepts a `str`. These
will often be used for filtering the values of entries in the measure
versions `dict` of the Home model.
"""
