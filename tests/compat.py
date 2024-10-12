from __future__ import annotations

import sys
import unittest
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any
from typing import TypeVar

# TestCase.enterContext() backport, source:
# https://adamj.eu/tech/2022/11/14/unittest-context-methods-python-3-11-backports/

_T = TypeVar("_T")

if sys.version_info < (3, 11):

    def _enter_context(cm: Any, addcleanup: Callable[..., None]) -> Any:
        # We look up the special methods on the type to match the with
        # statement.
        cls = type(cm)
        try:
            enter = cls.__enter__
            exit = cls.__exit__
        except AttributeError:  # pragma: no cover
            raise TypeError(
                f"'{cls.__module__}.{cls.__qualname__}' object does "
                f"not support the context manager protocol"
            ) from None
        result = enter(cm)
        addcleanup(exit, cm, None, None, None)
        return result


class EnterContextMixin(unittest.TestCase):
    if sys.version_info < (3, 11):

        def enterContext(self, cm: AbstractContextManager[_T]) -> _T:
            result: _T = _enter_context(cm, self.addCleanup)
            return result
