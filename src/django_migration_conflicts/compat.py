import builtins
import sys

if sys.version_info >= (3, 6):  # pragma: no cover
    ModuleNotFoundError = builtins.ModuleNotFoundError
else:
    ModuleNotFoundError = ImportError

if sys.version_info >= (3, 7):  # pragma: no cover

    def is_namespace_module(module):
        return module.__file__ is None


else:

    def is_namespace_module(module):
        return getattr(module, "__file__", None) is None
