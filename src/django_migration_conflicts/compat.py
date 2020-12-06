import sys

if sys.version_info >= (3, 7):  # pragma: no cover

    def is_namespace_module(module):
        return module.__file__ is None


else:  # pragma: no cover

    def is_namespace_module(module):
        return getattr(module, "__file__", None) is None
