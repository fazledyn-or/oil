#!/usr/bin/env python2
"""
func_misc.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import (value, value_str, value_t, value_e,
                                        scope_e)
from core import error
from core import ui
from core import vm
from frontend import match
from frontend import typed_args
from mycpp.mylib import NewDict, iteritems, log, tagswitch
from ysh import expr_eval, val_ops

from typing import TYPE_CHECKING, Dict, List, cast
if TYPE_CHECKING:
    from core import state
    from osh import glob_
    from osh import split

_ = log


class Len(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        x = rd.PosValue()
        rd.Done()

        UP_x = x
        with tagswitch(x) as case:
            if case(value_e.List):
                x = cast(value.List, UP_x)
                return value.Int(len(x.items))

            elif case(value_e.Dict):
                x = cast(value.Dict, UP_x)
                return value.Int(len(x.d))

            elif case(value_e.Str):
                x = cast(value.Str, UP_x)
                return value.Int(len(x.s))

        raise error.TypeErr(x, 'len() expected Str, List, or Dict',
                            rd.BlamePos())


class Join(vm._Callable):
    """Both free function join() and List->join() method."""

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        li = rd.PosList()
        delim = rd.OptionalStr(default_='')
        rd.Done()

        strs = []  # type: List[str]
        for i, el in enumerate(li):
            strs.append(val_ops.Stringify(el, rd.LeftParenToken()))

        return value.Str(delim.join(strs))


class Maybe(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        if val == value.Null:
            return value.List([])

        s = val_ops.ToStr(
            val, 'maybe() expected Str, but got %s' % value_str(val.tag()),
            rd.LeftParenToken())
        if len(s):
            return value.List([val])  # use val to avoid needlessly copy

        return value.List([])


class Type(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        return value.Str(ui.ValType(val))


class Bool(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        return value.Bool(val_ops.ToBool(val))


class Int(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                return val

            elif case(value_e.Bool):
                val = cast(value.Bool, UP_val)
                return value.Int(int(val.b))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)
                return value.Int(int(val.f))

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                if not match.LooksLikeInteger(val.s):
                    raise error.Expr('Cannot convert %s to Int' % val.s,
                                     rd.BlamePos())

                return value.Int(int(val.s))

        raise error.TypeErr(val, 'Int() expected Bool, Int, Float, or Str',
                            rd.BlamePos())


class Float(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                val = cast(value.Int, UP_val)
                return value.Float(float(val.i))

            elif case(value_e.Float):
                return val

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                if not match.LooksLikeFloat(val.s):
                    raise error.Expr('Cannot convert %s to Float' % val.s,
                                     rd.BlamePos())

                return value.Float(float(val.s))

        raise error.TypeErr(val, 'Float() expected Int, Float, or Str',
                            rd.BlamePos())


class Str_(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        # TODO: Should we call Stringify here?  That would handle Eggex.

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                val = cast(value.Int, UP_val)
                return value.Str(str(val.i))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)
                return value.Str(str(val.f))

            elif case(value_e.Str):
                return val

        raise error.TypeErr(val, 'Str() expected Str, Int, or Float',
                            rd.BlamePos())


class List_(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        l = []  # type: List[value_t]
        it = None  # type: val_ops._ContainerIter
        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.List):
                val = cast(value.List, UP_val)
                it = val_ops.ListIterator(val)

            elif case(value_e.Dict):
                val = cast(value.Dict, UP_val)
                it = val_ops.DictIterator(val)

            elif case(value_e.Range):
                val = cast(value.Range, UP_val)
                it = val_ops.RangeIterator(val)

            else:
                raise error.TypeErr(val,
                                    'List() expected Dict, List, or Range',
                                    rd.BlamePos())

        assert it is not None
        while not it.Done():
            l.append(it.FirstValue())
            it.Next()

        return value.List(l)


class Dict_(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Dict):
                d = NewDict()  # type: Dict[str, value_t]
                val = cast(value.Dict, UP_val)
                for k, v in iteritems(val.d):
                    d[k] = v

                return value.Dict(d)

            elif case(value_e.BashAssoc):
                d = NewDict()
                val = cast(value.BashAssoc, UP_val)
                for k, s in iteritems(val.d):
                    d[k] = value.Str(s)

                return value.Dict(d)

        raise error.TypeErr(val, 'Dict() expected List or Dict', rd.BlamePos())


class Split(vm._Callable):

    def __init__(self, splitter):
        # type: (split.SplitContext) -> None
        vm._Callable.__init__(self)
        self.splitter = splitter

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        s = rd.PosStr()

        ifs = rd.OptionalStr()

        rd.Done()

        l = [
            value.Str(elem)
            for elem in self.splitter.SplitForWordEval(s, ifs=ifs)
        ]  # type: List[value_t]
        return value.List(l)


class Glob(vm._Callable):

    def __init__(self, globber):
        # type: (glob_.Globber) -> None
        vm._Callable.__init__(self)
        self.globber = globber

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        s = rd.PosStr()
        rd.Done()

        out = []  # type: List[str]
        self.globber._Glob(s, out)

        l = [value.Str(elem) for elem in out]  # type: List[value_t]
        return value.List(l)


class Shvar_get(vm._Callable):
    """Look up with dynamic scope."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        name = rd.PosStr()
        rd.Done()
        return expr_eval.LookupVar(self.mem, name, scope_e.Dynamic,
                                   rd.LeftParenToken())


class Assert(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()

        msg = rd.OptionalStr(default_='')

        rd.Done()

        if not val_ops.ToBool(val):
            raise error.AssertionErr(msg, rd.LeftParenToken())

        return value.Null


class EvalExpr(vm._Callable):

    def __init__(self, expr_ev):
        # type: (expr_eval.ExprEvaluator) -> None
        self.expr_ev = expr_ev

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        lazy = rd.PosExpr()
        rd.Done()

        result = self.expr_ev.EvalExpr(lazy, rd.LeftParenToken())

        return result
