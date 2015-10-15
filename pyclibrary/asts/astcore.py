# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Provides basic functionality for AST object models and Transformers for
transorming from one model to another.

"""
import copy
from future.utils import with_metaclass
import collections


def flatten(iter):
    """Flattens nested iterators into a single iterator.
    This is a replacement for the "yield from" statement which is not supported
    in Python < 3.4.

    Its usage is like:

        def generator2(x):
            yield x

        def generator1():
            yield generator2(1)
            yield generator2(2)

        assert list(flatten(generator1())) == [1, 2]

    """
    stack = collections.deque()
    while True:
        try:
            item = next(iter)
        except StopIteration:
            if len(stack) == 0:
                return
            else:
                iter = stack.pop()
        else:
            if isinstance(item, collections.Iterator):
                stack.append(iter)
                iter = item
            else:
                yield item



class AstNodeMeta(type):

    def __new__(metacls, name, parents, attrs):

        def __init__(self, *args, **argv):
            for req_argv in slots[len(args):]:
                if req_argv not in argv:
                    raise TypeError('missing parameter {!r}'
                                    .format(req_argv))
                args += (argv.pop(req_argv),)
            for parname, parval in zip(slots, args):
                setattr(self, parname, parval)
            super(cls, self).__init__(*args[len(slots):], **argv)

        def __repr__(self):
            superRepr = super(cls, self).__repr__()
            _, rest = superRepr.split('(', 1)
            paramStrs = [repr(getattr(self, an)) for an in slots]
            if len(rest) > 1:
                # add parameters from parent class (without trailing ')')
                paramStrs.append(rest[:-1])
            return cls.__name__ + '(' + ', '.join(paramStrs) + ')'

        def __eq__(self, other):
            return (super(cls, self).__eq__(other)  and
                    all(getattr(self, an) == getattr(other, an)
                        for an in slots))

        attrs.setdefault('__init__', __init__)
        attrs.setdefault('__repr__', __repr__)
        attrs.setdefault('__eq__', __eq__)
        slots = attrs.setdefault('__slots__', ())
        cls = type.__new__(metacls, name, parents, attrs)
        return cls


class AstNode(with_metaclass(AstNodeMeta, object)):
    """Provides automatic support for __init__/__repr__/__eq__/copy by
    analysing the __slots__ parameter.

    Sample definition:
    class Demo(DataObject):
        __slots__ = ('field1', 'field2')
    """

    __slots__ = ()

    def __init__(self):
        pass

    def __repr__(self):
        return "DataObject()"

    def __eq__(self, other):
        return type(self) == type(other)

    def __ne__(self, other):
        return not self == other

    def copy(self):
        """Creastes a shallow copy of the object
        """
        return copy.copy(self)


class TransformerMeta(type):
    """This metaclass collects all registered AST class transformation
    methods.

    """

    def __new__(cls, name, parents, attrs):
        ast_dict = {}
        for attr in attrs.values():
            if callable(attr) and hasattr(attr, 'ast_class'):
                ast_dict[attr.ast_class] = attr
        attrs['AST_DICT'] = ast_dict
        return type.__new__(cls, name, parents, attrs)


class Transformer(with_metaclass(TransformerMeta, object)):
    """Baseclass for transforming a objectmodel to another

    """

    AST_DICT = {}    # will be filled by metaclass

    class UnsupportedClassError(Exception):
        """The object model to be transformed contained a class that cannot
        be handled
        """

    def transform(self, ast, *ctx):
        """Transforms a single AST object under the given context 'ctx' with
        the parametrization of this Transformer object into multiple
        destinations AST objects.

        The number of yielded objects may varie from 0 to n.

        """
        for cls in type(ast).__mro__:
            try:
                fmtFunc = self.AST_DICT[cls]
            except KeyError:
                pass
            else:
                return fmtFunc(self, ast, *ctx)
        else:
            raise self.UnsupportedClassError(
                '{!r} has no transormation rule for class {!r}'
                .format(type(self).__name__, type(ast).__name__))

    def __call__(self, ast, *ctx):
        """This is a shortcut for .transform(), that enforces that exactly one
        object is yielded. Instead of returnung an iterator, this method
        returns this single object.

        """
        result, = self.transform(ast, *ctx)
        return result

    @staticmethod
    def register(ast_class):
        def wrapper(func):
            func.ast_class = ast_class
            return func
        return wrapper
