import functools
from typing import Callable, TypeVar, ParamSpec, Concatenate

from src.app.views import View
from src.app.models import Model
from src.etrm.exceptions import UnauthorizedError


_T = TypeVar('_T')
_P = ParamSpec('_P')


class BaseController:
    def __init__(self, view: View, model: Model):
        self.view_root = view
        self.model_root = model


_DEC_ARGS = Callable[_P, _T]
"""General decorator argument type for outer level decorator
functions.

Use when type-hinting the arguments for decorators that require
specific arguments (i.e., `self`).
"""


_BC_DEC_RETV = Callable[Concatenate[BaseController, _P], _T]
"""Specific decorator return value type that specifies the argument
and return types of the inner-most function.

Use when type-hinting a decorator that requires the caller method to
reside in a class that extends `BaseController`.
"""


def etrm_request(func: Callable[_P, _T]) -> _BC_DEC_RETV:
    def wrapper(self: BaseController,
                *args: _P.args,
                **kwargs: _P.kwargs
               ) -> _T:
        if self.model_root.connection is None:
            raise UnauthorizedError()
        value: _T = func(self, *args, **kwargs)
        return value
    return wrapper
