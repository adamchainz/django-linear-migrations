import sys

if sys.version_info >= (3, 7):

    def is_namespace_module(module):
        return module.__file__ is None


else:

    def is_namespace_module(module):
        return getattr(module, "__file__", None) is None
