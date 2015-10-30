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
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

import copy
import collections

from future.utils import with_metaclass


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
    """Metaclass for ast nodes.

    """

    def __new__(metacls, name, parents, attrs):

        slots = attrs.setdefault('__slots__', ())

        defaults = {}
        for p in parents:
            defaults.update(getattr(p, '__defaults__', {}))
        defaults.update(attrs.get('__defaults__', {}))
        attrs['__defaults__'] = defaults

        def __repr__(self):
            super_repr = super(cls, self).__repr__()
            _, rest = super_repr.split('(', 1)
            param_strs = [an + '=' + repr(getattr(self, an)) for an in slots]
            if len(rest) > 1:
                # add parameters from parent class (without trailing ')')
                param_strs.append(rest[:-1])
            return cls.__name__ + '(' + ', '.join(param_strs) + ')'

        def __eq__(self, other):
            return (super(cls, self).__eq__(other) and
                    all(getattr(self, an) == getattr(other, an)
                        for an in slots))

        attrs.setdefault('__repr__', __repr__)
        attrs.setdefault('__eq__', __eq__)
        cls = type.__new__(metacls, name, parents, attrs)
        return cls


class AstNode(with_metaclass(AstNodeMeta, object)):
    """Provides automatic support for __init__/__repr__/__eq__/copy by
    analysing the __slots__ parameter.

    All subsclasses are automatically slotted.

    Default values for attributes can be specified as callable in a dictionary
    stored under __defaults__.

    Sample definition:
    class Demo(DataObject):
        __slots__ = ('field1', 'field2')

    """
    __slots__ = ()
    __default__ = {}

    def __init__(self, *args, **kwargs):
        seen = set()
        for k, v in zip(self.__slots__, args):
            setattr(self, k, v)
            seen.add(k)
        for k, v in self.__defaults__.items():
            if k not in seen:
                if k in kwargs:
                    v = kwargs[k]
                else:
                    v = v()
                setattr(self, k, v)

    def __ne__(self, other):
        return not self == other

    def copy(self):
        """Creates a shallow copy of the object.

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
                '{!r} has no transformation rule for class {!r}'
                .format(type(self).__name__, type(ast).__name__))

    def __call__(self, ast, *ctx):
        """This is a shortcut for .transform(), that enforces that exactly one
        object is yielded. Instead of returning an iterator, this method
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
