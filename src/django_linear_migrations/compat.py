from __future__ import annotations

import ast
import io
import sys
from typing import no_type_check

if sys.version_info >= (3, 8):
    # Bridge the change from ast.Str to ast.Constant

    ast_constant_type = ast.Constant

    def is_ast_constant_str(node: ast.AST) -> bool:
        return isinstance(node, ast.Constant) and isinstance(node.value, str)

    def get_ast_constant_str_value(node: ast.Constant) -> str:
        return node.value

    def make_ast_constant_str(value: str) -> ast.Constant:
        return ast.Constant(value=value, kind=None)

else:

    ast_constant_type = ast.Str

    def is_ast_constant_str(node: ast.AST) -> bool:
        return isinstance(node, ast.Str)

    def get_ast_constant_str_value(node: ast.Str) -> str:
        return node.s

    def make_ast_constant_str(value: str) -> ast.Str:
        return ast.Str(s=value)


if sys.version_info >= (3, 9):
    ast_unparse = ast.unparse
else:

    def ast_unparse(ast_obj: ast.AST) -> str:
        out = io.StringIO()
        Unparser(ast_obj, out)
        return out.getvalue().strip()

    # Copied from
    # https://github.com/python/cpython/blob/3.8/Tools/parser/unparse.py
    # Which got adapted into ast.unparse in Python 3.9

    # Large float and imaginary literals get turned into infinities in the AST.
    # We unparse those infinities to INFSTR.
    INFSTR = "1e" + repr(sys.float_info.max_10_exp + 1)

    @no_type_check
    def interleave(inter, f, seq):  # pragma: no cover
        """Call f on each item in seq, calling inter() in between."""
        seq = iter(seq)
        try:
            f(next(seq))
        except StopIteration:
            pass
        else:
            for x in seq:
                inter()
                f(x)

    class Unparser:  # pragma: no cover
        """Methods in this class recursively traverse an AST and
        output source code for the abstract syntax; original formatting
        is disregarded."""

        @no_type_check
        def __init__(self, tree, file=sys.stdout):
            """Unparser(tree, file=sys.stdout) -> None.
            Print the source for tree to file."""
            self.f = file
            self._indent = 0
            self.dispatch(tree)
            print("", file=self.f)
            self.f.flush()

        @no_type_check
        def fill(self, text=""):
            "Indent a piece of text, according to the current indentation level"
            self.f.write("\n" + "    " * self._indent + text)

        @no_type_check
        def write(self, text):
            "Append a piece of text to the current line."
            self.f.write(text)

        @no_type_check
        def enter(self):
            "Print ':', and increase the indentation."
            self.write(":")
            self._indent += 1

        @no_type_check
        def leave(self):
            "Decrease the indentation level."
            self._indent -= 1

        @no_type_check
        def dispatch(self, tree):
            "Dispatcher function, dispatching tree type T to method _T."
            if isinstance(tree, list):
                for t in tree:
                    self.dispatch(t)
                return
            meth = getattr(self, "_" + tree.__class__.__name__)
            meth(tree)

        # ############## Unparsing methods ######################
        # There should be one method per concrete grammar type #
        # Constructors should be grouped by sum type. Ideally, #
        # this would follow the order in the grammar, but      #
        # currently doesn't.                                   #
        # #######################################################

        @no_type_check
        def _Module(self, tree):
            for stmt in tree.body:
                self.dispatch(stmt)

        # stmt
        @no_type_check
        def _Expr(self, tree):
            self.fill()
            self.dispatch(tree.value)

        @no_type_check
        def _NamedExpr(self, tree):
            self.write("(")
            self.dispatch(tree.target)
            self.write(" := ")
            self.dispatch(tree.value)
            self.write(")")

        @no_type_check
        def _Import(self, t):
            self.fill("import ")
            interleave(lambda: self.write(", "), self.dispatch, t.names)

        @no_type_check
        def _ImportFrom(self, t):
            self.fill("from ")
            self.write("." * t.level)
            if t.module:
                self.write(t.module)
            self.write(" import ")
            interleave(lambda: self.write(", "), self.dispatch, t.names)

        @no_type_check
        def _Assign(self, t):
            self.fill()
            for target in t.targets:
                self.dispatch(target)
                self.write(" = ")
            self.dispatch(t.value)

        @no_type_check
        def _AugAssign(self, t):
            self.fill()
            self.dispatch(t.target)
            self.write(" " + self.binop[t.op.__class__.__name__] + "= ")
            self.dispatch(t.value)

        @no_type_check
        def _AnnAssign(self, t):
            self.fill()
            if not t.simple and isinstance(t.target, ast.Name):
                self.write("(")
            self.dispatch(t.target)
            if not t.simple and isinstance(t.target, ast.Name):
                self.write(")")
            self.write(": ")
            self.dispatch(t.annotation)
            if t.value:
                self.write(" = ")
                self.dispatch(t.value)

        @no_type_check
        def _Return(self, t):
            self.fill("return")
            if t.value:
                self.write(" ")
                self.dispatch(t.value)

        @no_type_check
        def _Pass(self, t):
            self.fill("pass")

        @no_type_check
        def _Break(self, t):
            self.fill("break")

        @no_type_check
        def _Continue(self, t):
            self.fill("continue")

        @no_type_check
        def _Delete(self, t):
            self.fill("del ")
            interleave(lambda: self.write(", "), self.dispatch, t.targets)

        @no_type_check
        def _Assert(self, t):
            self.fill("assert ")
            self.dispatch(t.test)
            if t.msg:
                self.write(", ")
                self.dispatch(t.msg)

        @no_type_check
        def _Global(self, t):
            self.fill("global ")
            interleave(lambda: self.write(", "), self.write, t.names)

        @no_type_check
        def _Nonlocal(self, t):
            self.fill("nonlocal ")
            interleave(lambda: self.write(", "), self.write, t.names)

        @no_type_check
        def _Await(self, t):
            self.write("(")
            self.write("await")
            if t.value:
                self.write(" ")
                self.dispatch(t.value)
            self.write(")")

        @no_type_check
        def _Yield(self, t):
            self.write("(")
            self.write("yield")
            if t.value:
                self.write(" ")
                self.dispatch(t.value)
            self.write(")")

        @no_type_check
        def _YieldFrom(self, t):
            self.write("(")
            self.write("yield from")
            if t.value:
                self.write(" ")
                self.dispatch(t.value)
            self.write(")")

        @no_type_check
        def _Raise(self, t):
            self.fill("raise")
            if not t.exc:
                assert not t.cause
                return
            self.write(" ")
            self.dispatch(t.exc)
            if t.cause:
                self.write(" from ")
                self.dispatch(t.cause)

        @no_type_check
        def _Try(self, t):
            self.fill("try")
            self.enter()
            self.dispatch(t.body)
            self.leave()
            for ex in t.handlers:
                self.dispatch(ex)
            if t.orelse:
                self.fill("else")
                self.enter()
                self.dispatch(t.orelse)
                self.leave()
            if t.finalbody:
                self.fill("finally")
                self.enter()
                self.dispatch(t.finalbody)
                self.leave()

        @no_type_check
        def _ExceptHandler(self, t):
            self.fill("except")
            if t.type:
                self.write(" ")
                self.dispatch(t.type)
            if t.name:
                self.write(" as ")
                self.write(t.name)
            self.enter()
            self.dispatch(t.body)
            self.leave()

        @no_type_check
        def _ClassDef(self, t):
            self.write("\n")
            for deco in t.decorator_list:
                self.fill("@")
                self.dispatch(deco)
            self.fill("class " + t.name)
            self.write("(")
            comma = False
            for e in t.bases:
                if comma:
                    self.write(", ")
                else:
                    comma = True
                self.dispatch(e)
            for e in t.keywords:
                if comma:
                    self.write(", ")
                else:
                    comma = True
                self.dispatch(e)
            self.write(")")

            self.enter()
            self.dispatch(t.body)
            self.leave()

        @no_type_check
        def _FunctionDef(self, t):
            self.__FunctionDef_helper(t, "def")

        @no_type_check
        def _AsyncFunctionDef(self, t):
            self.__FunctionDef_helper(t, "async def")

        @no_type_check
        def __FunctionDef_helper(self, t, fill_suffix):
            self.write("\n")
            for deco in t.decorator_list:
                self.fill("@")
                self.dispatch(deco)
            def_str = fill_suffix + " " + t.name + "("
            self.fill(def_str)
            self.dispatch(t.args)
            self.write(")")
            if t.returns:
                self.write(" -> ")
                self.dispatch(t.returns)
            self.enter()
            self.dispatch(t.body)
            self.leave()

        @no_type_check
        def _For(self, t):
            self.__For_helper("for ", t)

        @no_type_check
        def _AsyncFor(self, t):
            self.__For_helper("async for ", t)

        @no_type_check
        def __For_helper(self, fill, t):
            self.fill(fill)
            self.dispatch(t.target)
            self.write(" in ")
            self.dispatch(t.iter)
            self.enter()
            self.dispatch(t.body)
            self.leave()
            if t.orelse:
                self.fill("else")
                self.enter()
                self.dispatch(t.orelse)
                self.leave()

        @no_type_check
        def _If(self, t):
            self.fill("if ")
            self.dispatch(t.test)
            self.enter()
            self.dispatch(t.body)
            self.leave()
            # collapse nested ifs into equivalent elifs.
            while t.orelse and len(t.orelse) == 1 and isinstance(t.orelse[0], ast.If):
                t = t.orelse[0]
                self.fill("elif ")
                self.dispatch(t.test)
                self.enter()
                self.dispatch(t.body)
                self.leave()
            # final else
            if t.orelse:
                self.fill("else")
                self.enter()
                self.dispatch(t.orelse)
                self.leave()

        @no_type_check
        def _While(self, t):
            self.fill("while ")
            self.dispatch(t.test)
            self.enter()
            self.dispatch(t.body)
            self.leave()
            if t.orelse:
                self.fill("else")
                self.enter()
                self.dispatch(t.orelse)
                self.leave()

        @no_type_check
        def _With(self, t):
            self.fill("with ")
            interleave(lambda: self.write(", "), self.dispatch, t.items)
            self.enter()
            self.dispatch(t.body)
            self.leave()

        @no_type_check
        def _AsyncWith(self, t):
            self.fill("async with ")
            interleave(lambda: self.write(", "), self.dispatch, t.items)
            self.enter()
            self.dispatch(t.body)
            self.leave()

        # expr
        @no_type_check
        def _JoinedStr(self, t):
            self.write("f")
            string = io.StringIO()
            self._fstring_JoinedStr(t, string.write)
            self.write(repr(string.getvalue()))

        @no_type_check
        def _FormattedValue(self, t):
            self.write("f")
            string = io.StringIO()
            self._fstring_FormattedValue(t, string.write)
            self.write(repr(string.getvalue()))

        @no_type_check
        def _fstring_JoinedStr(self, t, write):
            for value in t.values:
                meth = getattr(self, "_fstring_" + type(value).__name__)
                meth(value, write)

        @no_type_check
        def _fstring_Constant(self, t, write):
            assert isinstance(t.value, str)
            value = t.value.replace("{", "{{").replace("}", "}}")
            write(value)

        @no_type_check
        def _fstring_FormattedValue(self, t, write):
            write("{")
            expr = io.StringIO()
            Unparser(t.value, expr)
            expr = expr.getvalue().rstrip("\n")
            if expr.startswith("{"):
                write(" ")  # Separate pair of opening brackets as "{ {"
            write(expr)
            if t.conversion != -1:
                conversion = chr(t.conversion)
                assert conversion in "sra"
                write(f"!{conversion}")
            if t.format_spec:
                write(":")
                meth = getattr(self, "_fstring_" + type(t.format_spec).__name__)
                meth(t.format_spec, write)
            write("}")

        @no_type_check
        def _Name(self, t):
            self.write(t.id)

        @no_type_check
        def _write_constant(self, value):
            if isinstance(value, (float, complex)):
                # Substitute overflowing decimal literal for AST infinities.
                self.write(repr(value).replace("inf", INFSTR))
            else:
                self.write(repr(value))

        # From Python 3.7:
        @no_type_check
        def _Str(self, tree):
            self.write(repr(tree.s))

        # From Python 3.8:
        @no_type_check
        def _Constant(self, t):
            value = t.value
            if isinstance(value, tuple):
                self.write("(")
                if len(value) == 1:
                    self._write_constant(value[0])
                    self.write(",")
                else:
                    interleave(lambda: self.write(", "), self._write_constant, value)
                self.write(")")
            elif value is ...:
                self.write("...")
            else:
                if t.kind == "u":
                    self.write("u")
                self._write_constant(t.value)

        @no_type_check
        def _List(self, t):
            self.write("[")
            interleave(lambda: self.write(", "), self.dispatch, t.elts)
            self.write("]")

        @no_type_check
        def _ListComp(self, t):
            self.write("[")
            self.dispatch(t.elt)
            for gen in t.generators:
                self.dispatch(gen)
            self.write("]")

        @no_type_check
        def _GeneratorExp(self, t):
            self.write("(")
            self.dispatch(t.elt)
            for gen in t.generators:
                self.dispatch(gen)
            self.write(")")

        @no_type_check
        def _SetComp(self, t):
            self.write("{")
            self.dispatch(t.elt)
            for gen in t.generators:
                self.dispatch(gen)
            self.write("}")

        @no_type_check
        def _DictComp(self, t):
            self.write("{")
            self.dispatch(t.key)
            self.write(": ")
            self.dispatch(t.value)
            for gen in t.generators:
                self.dispatch(gen)
            self.write("}")

        @no_type_check
        def _comprehension(self, t):
            if t.is_async:
                self.write(" async for ")
            else:
                self.write(" for ")
            self.dispatch(t.target)
            self.write(" in ")
            self.dispatch(t.iter)
            for if_clause in t.ifs:
                self.write(" if ")
                self.dispatch(if_clause)

        @no_type_check
        def _IfExp(self, t):
            self.write("(")
            self.dispatch(t.body)
            self.write(" if ")
            self.dispatch(t.test)
            self.write(" else ")
            self.dispatch(t.orelse)
            self.write(")")

        @no_type_check
        def _Set(self, t):
            assert t.elts  # should be at least one element
            self.write("{")
            interleave(lambda: self.write(", "), self.dispatch, t.elts)
            self.write("}")

        @no_type_check
        def _Dict(self, t):
            self.write("{")

            def write_key_value_pair(k, v):
                self.dispatch(k)
                self.write(": ")
                self.dispatch(v)

            def write_item(item):
                k, v = item
                if k is None:
                    # for dictionary unpacking operator in dicts {**{'y': 2}}
                    # see PEP 448 for details
                    self.write("**")
                    self.dispatch(v)
                else:
                    write_key_value_pair(k, v)

            interleave(lambda: self.write(", "), write_item, zip(t.keys, t.values))
            self.write("}")

        @no_type_check
        def _Tuple(self, t):
            self.write("(")
            if len(t.elts) == 1:
                elt = t.elts[0]
                self.dispatch(elt)
                self.write(",")
            else:
                interleave(lambda: self.write(", "), self.dispatch, t.elts)
            self.write(")")

        unop = {"Invert": "~", "Not": "not", "UAdd": "+", "USub": "-"}

        @no_type_check
        def _UnaryOp(self, t):
            self.write("(")
            self.write(self.unop[t.op.__class__.__name__])
            self.write(" ")
            self.dispatch(t.operand)
            self.write(")")

        binop = {
            "Add": "+",
            "Sub": "-",
            "Mult": "*",
            "MatMult": "@",
            "Div": "/",
            "Mod": "%",
            "LShift": "<<",
            "RShift": ">>",
            "BitOr": "|",
            "BitXor": "^",
            "BitAnd": "&",
            "FloorDiv": "//",
            "Pow": "**",
        }

        @no_type_check
        def _BinOp(self, t):
            self.write("(")
            self.dispatch(t.left)
            self.write(" " + self.binop[t.op.__class__.__name__] + " ")
            self.dispatch(t.right)
            self.write(")")

        cmpops = {
            "Eq": "==",
            "NotEq": "!=",
            "Lt": "<",
            "LtE": "<=",
            "Gt": ">",
            "GtE": ">=",
            "Is": "is",
            "IsNot": "is not",
            "In": "in",
            "NotIn": "not in",
        }

        @no_type_check
        def _Compare(self, t):
            self.write("(")
            self.dispatch(t.left)
            for o, e in zip(t.ops, t.comparators):
                self.write(" " + self.cmpops[o.__class__.__name__] + " ")
                self.dispatch(e)
            self.write(")")

        boolops = {ast.And: "and", ast.Or: "or"}

        @no_type_check
        def _BoolOp(self, t):
            self.write("(")
            s = " %s " % self.boolops[t.op.__class__]
            interleave(lambda: self.write(s), self.dispatch, t.values)
            self.write(")")

        @no_type_check
        def _Attribute(self, t):
            self.dispatch(t.value)
            # Special case: 3.__abs__() is a syntax error, so if t.value
            # is an integer literal then we need to either parenthesize
            # it or add an extra space to get 3 .__abs__().
            if isinstance(t.value, ast.Constant) and isinstance(t.value.value, int):
                self.write(" ")
            self.write(".")
            self.write(t.attr)

        @no_type_check
        def _Call(self, t):
            self.dispatch(t.func)
            self.write("(")
            comma = False
            for e in t.args:
                if comma:
                    self.write(", ")
                else:
                    comma = True
                self.dispatch(e)
            for e in t.keywords:
                if comma:
                    self.write(", ")
                else:
                    comma = True
                self.dispatch(e)
            self.write(")")

        @no_type_check
        def _Subscript(self, t):
            self.dispatch(t.value)
            self.write("[")
            if (
                isinstance(t.slice, ast.Index)
                and isinstance(t.slice.value, ast.Tuple)
                and t.slice.value.elts
            ):
                if len(t.slice.value.elts) == 1:
                    elt = t.slice.value.elts[0]
                    self.dispatch(elt)
                    self.write(",")
                else:
                    interleave(
                        lambda: self.write(", "), self.dispatch, t.slice.value.elts
                    )
            else:
                self.dispatch(t.slice)
            self.write("]")

        @no_type_check
        def _Starred(self, t):
            self.write("*")
            self.dispatch(t.value)

        # slice
        @no_type_check
        def _Ellipsis(self, t):
            self.write("...")

        @no_type_check
        def _Index(self, t):
            self.dispatch(t.value)

        @no_type_check
        def _Slice(self, t):
            if t.lower:
                self.dispatch(t.lower)
            self.write(":")
            if t.upper:
                self.dispatch(t.upper)
            if t.step:
                self.write(":")
                self.dispatch(t.step)

        @no_type_check
        def _ExtSlice(self, t):
            if len(t.dims) == 1:
                elt = t.dims[0]
                self.dispatch(elt)
                self.write(",")
            else:
                interleave(lambda: self.write(", "), self.dispatch, t.dims)

        # argument
        @no_type_check
        def _arg(self, t):
            self.write(t.arg)
            if t.annotation:
                self.write(": ")
                self.dispatch(t.annotation)

        # others
        @no_type_check
        def _arguments(self, t):
            first = True
            # normal arguments
            all_args = t.posonlyargs + t.args
            defaults = [None] * (len(all_args) - len(t.defaults)) + t.defaults
            for index, elements in enumerate(zip(all_args, defaults), 1):
                a, d = elements
                if first:
                    first = False
                else:
                    self.write(", ")
                self.dispatch(a)
                if d:
                    self.write("=")
                    self.dispatch(d)
                if index == len(t.posonlyargs):
                    self.write(", /")

            # varargs, or bare '*' if no varargs but keyword-only arguments present
            if t.vararg or t.kwonlyargs:
                if first:
                    first = False
                else:
                    self.write(", ")
                self.write("*")
                if t.vararg:
                    self.write(t.vararg.arg)
                    if t.vararg.annotation:
                        self.write(": ")
                        self.dispatch(t.vararg.annotation)

            # keyword-only arguments
            if t.kwonlyargs:
                for a, d in zip(t.kwonlyargs, t.kw_defaults):
                    if first:
                        first = False
                    else:
                        self.write(", ")
                    self.dispatch(a),
                    if d:
                        self.write("=")
                        self.dispatch(d)

            # kwargs
            if t.kwarg:
                if first:
                    first = False
                else:
                    self.write(", ")
                self.write("**" + t.kwarg.arg)
                if t.kwarg.annotation:
                    self.write(": ")
                    self.dispatch(t.kwarg.annotation)

        @no_type_check
        def _keyword(self, t):
            if t.arg is None:
                self.write("**")
            else:
                self.write(t.arg)
                self.write("=")
            self.dispatch(t.value)

        @no_type_check
        def _Lambda(self, t):
            self.write("(")
            self.write("lambda ")
            self.dispatch(t.args)
            self.write(": ")
            self.dispatch(t.body)
            self.write(")")

        @no_type_check
        def _alias(self, t):
            self.write(t.name)
            if t.asname:
                self.write(" as " + t.asname)

        @no_type_check
        def _withitem(self, t):
            self.dispatch(t.context_expr)
            if t.optional_vars:
                self.write(" as ")
                self.dispatch(t.optional_vars)
