# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""This module contains a AST classes for python code.

The AST follows closely the python 3 AST it is up to consumer to translate it
when possible to valid python 2.

The organisation of this module and its documentation are strongly inspired by
https://greentreesnakes.readthedocs.org/en/latest/nodes.html

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from future.builtins import str, bytes

from .astcore import AstNode  # All subclasses are slotted by default


# =============================================================================
# --- Base nodes --------------------------------------------------------------
# =============================================================================

class PyAstNode(AstNode):
    """Base class for all nodes representing a Python ast.

    """
    pass


class StatementNode(PyAstNode):
    """Base class for statement like nodes.

    """
    pass


class ExpressionNode(PyAstNode):
    """Base class for expressions like nodes.

    """
    pass


# =============================================================================
# --- Literal values ----------------------------------------------------------
# =============================================================================

class LiteralNode(ExpressionNode):
    """Base class for literal expressions.

    """
    pass


class Num(LiteralNode):
    """Node for numerical value represented as python objects.

    """
    __slots__ = ('value')


class Int(Num): __defaults__ = {'value': int}
class Float(Num): __defaults__ = {'value': float}


class Str(LiteralNode):
    """Node representing a Python string

    """
    __slots__ = ('string')
    __defaults__ = {'string': str}


class Bytes(LiteralNode):
    """Node representing a byte array. Python 3 only

    """
    __slots__ = ('bytes')
    __defaults__ = {'bytes': bytes}


class Tuple(LiteralNode):
    """Node reprensting a tuple.

    Context can be either a Store instance ("(a, b) = c") or a Load one.

    """
    __slots__ = ('elts', 'ctx')
    __defaults__ = {'elts': list}


class List(LiteralNode):
    """Node reprensting a list.


    Context can be either a Store instance ("[a, b] = c") or a Load one.

    """
    __slots__ = ('elts', 'ctx')
    __defaults__ = {'elts': list}


class Dict(LiteralNode):
    """Node representing a dictionary.

    """
    __slots__ = ('keys', 'values')
    __defaults__ = {'keys': list, 'values': list}


class Set(LiteralNode):
    """Node reprensting a set.

    """
    __slots__ = ('elts',)
    __defaults__ = {'elts': list}


class Ellipsis(LiteralNode):
    pass


# =============================================================================
# --- Variables ---------------------------------------------------------------
# =============================================================================

class Context(PyAstNode):
    """Context helping determining the operation performed on a variable.

    """
    pass


class Load(Context): pass
class Store(Context): pass
class Del(Context): pass


class Name(ExpressionNode):
    """A variable name.

    Attributes
    ----------
    id : unicode
        Name of the variable.

    ctx : Context
        Context in which the variable is referenced (is it
        loaded/stored/deleted ?)

    """
    __slots__ = ('id', 'ctx')
    __defaults__ = {'ctx': Load}


class Starred(ExpressionNode):
    """Node representing a starred variable reference.

    ex : a, *b = c (Python 3.5 only, or in Call)

    """
    __slots__ = ('value', 'ctx')

# =============================================================================
# --- Expressions -------------------------------------------------------------
# =============================================================================


class Expr(ExpressionNode):
    """When an expression, such as a function call, appears as a statement by
    itself (an expression statement), with its return value not used or stored,
    it is wrapped in this container.

    ex : "-a"

    """
    __slots__ = ('value',)


class UnnaryOp(ExpressionNode):
    """Node representing a unary operation.

    Attributes
    ----------
    op : UnaryOperator
        Operator applied on the operand.

    operand : ExpressionNode
        Expression on which to apply the operation.

    """
    __slots__ = ('op', 'operand',)


# --- Unary operators
class UnaryOperator(PyAstNode): pass
class UAdd(UnaryOperator): pass
class USub(UnaryOperator): pass
class Not(UnaryOperator): pass
class Invert(UnaryOperator): pass


class BinaryOp(ExpressionNode):
    """Node representing a binary opertation.

    Attributes
    ----------
    left : ExpressionNode
        Left member of the operation.

    op : BinaryOperator
        Operator applied on the operand.

    right : ExpressionNode
        Right member of the operation.

    """
    __slots__ = ('left', 'op', 'right')


# --- Binary operators
class BinaryOperator(PyAstNode): pass
class Add(BinaryOperator): pass
class Sub(BinaryOperator): pass
class Mul(BinaryOperator): pass
class Div(BinaryOperator): pass
class FloorDiv(BinaryOperator): pass
class Mod(BinaryOperator): pass
class Pow(BinaryOperator): pass
class RShift(BinaryOperator): pass
class LShift(BinaryOperator): pass
class BitOr(BinaryOperator): pass
class BitXor(BinaryOperator): pass
class BitAnd(BinaryOperator): pass


class BoolOp(ExpressionNode):
    """Node representing a binary opertation.

    Attributes
    ----------
    op : BoolOperator
        Operator applied on the values.

    values : list[ExpressionNode]
        Expressions on which to apply the operator. This allow to use a single
        node for expression like "a and b and c".

    """
    __slots__ = ('op', 'values')
    __defaults__ = {'values': list}


# --- Binary operators
class BoolOperator(PyAstNode): pass
class And(BoolOperator): pass
class Or(BoolOperator): pass


class Compare(ExpressionNode):
    """Node reprenseting  comparison.

    The construction is weird as noted in the Python AST definition.

    Attributes
    ----------
    left : ExpressionNode
        First expression in the comparison.

    op : ComparisonOperator
        Operator to use in the comparison

    comparators : list[ExpressionNode]
        List of expression to compare. This is a list to use a single node
        for 'a < b < c'. (b and c are in the comparators member).

    """
    __slots__ = ('left', 'op', 'comparators')
    __defaults__ = {'comparators': list}


# --- Comparison operators
class ComparisonOperator(PyAstNode): pass
class Eq(ComparisonOperator): pass
class NotEq(ComparisonOperator): pass
class Lt(ComparisonOperator): pass
class LtE(ComparisonOperator): pass
class Gt(ComparisonOperator): pass
class GtE(ComparisonOperator): pass
class Is(ComparisonOperator): pass
class NotIs(ComparisonOperator): pass
class In(ComparisonOperator): pass
class NotIn(ComparisonOperator): pass


class Call(ExpressionNode):
    """Node representing a call of a callable.

    Attributes
    ----------
    func : ExpressionNode
        Function object often a Name or Attribute node.

    args : list[ExpressionNode]
        List of the function arguments.

    kwargs : list[keyword]
        List of keyword arguments passed as keyword instances.

    Notes
    -----
    This node use the Python 3.5 semantic in which *args are represented using
    Starred and **kwargs using a keyword whose arg is None.

    """
    __slots__ = ('func', 'args', 'keywords')
    __defaults__ = {'args': list, 'keyword': list}


class keyword(PyAstNode):
    """Node representing a keyword argument.

    Attributes
    ----------
    arg : unicode or None
        Name of the keyword argument. If None the value is unpacked as a
        dictionary.

    value : ExpressionNode
        Value of the argument.

    Notes
    -----
    This follows the python 3.5 semantics, so that if arg is None this should
    be considered as dictionary unpacking.

    """
    __slots__ = ('arg', 'value')


class IfExp(ExpressionNode):
    """Node representing "a if b else c".

    Attributes
    ----------
    test : ExpressionNode
        Test appearing after the if.

    body : ExpressionNode
        Result in case test evaluates to True.

    orelse : ExpressionNode
        Result in case test evaluates to False.

    """
    __slots__ = ('test', 'body', 'orelse')


class Attribute(ExpressionNode):
    """Node representing an attribute access.

    Attributes
    ----------
    value : ExpressionNode
        Object whose attribute needs to be accessed.

    attr : unicode
        Name of the attribute.

    ctx : Context
        Context in which the attribute is accessed (is it
        loaded/stored/deleted)

    """
    __slots__ = ('value', 'attr', 'ctx')


# =============================================================================
# --- Subscripting ------------------------------------------------------------
# =============================================================================

class Subscript(ExpressionNode):
    """Node representing 'a[i]'.

    Attributes
    ----------
    value : ExpressionNode
        Object whose item needs to be accessed.

    slice : SliceNnode
        Index or slice of the object(s) being accessed.

    ctx : Context
        Context in which the item is accessed (is it loaded/stored/deleted)

    """
    __slots__ = ('value', 'slice', 'ctx')


# --- Slices
class SliceNode(PyAstNode):
    """Base class for node which can be used as slice in a Subscript.

    """
    pass


class Index(SliceNode): __slots__ = ('value',)
class Slice(SliceNode): __slots__ = ('lower', 'upper', 'step')
class ExtSlice(SliceNode):
    __slots__ = ('dims',)
    __defaults = {'dims': list}


# =============================================================================
# --- Comprehensions ----------------------------------------------------------
# =============================================================================

# TODO add later


# =============================================================================
# --- Statements --------------------------------------------------------------
# =============================================================================

class Assign(StatementNode):
    """Node representing an assignment.

    Attributes
    ----------
    targets : list[ExpressionNode]
        Nodes to which assign value. Multiple nodes in targets represents
        assigning the same value to each. Unpacking is represented by putting a
        Tuple or List within targets.

    value : ExpressionNode
        Value to assign to the targets.

    """
    __slots__ = ('targets', 'value')
    __defaults__ = {'targets': list}


class AugAssign(StatementNode):
    """Node represented an augmented assignment (+=).

    Notes
    -----
    The op attributes can be any BinaryOp instance.

    """
    __slots__ = ('target', 'op', 'value')


class Raise(StatementNode):
    """Node representing an exception raising.

    Attributes
    ----------
    exc : ExpressionNode or None
        Exception to raise. This is generally a Call or Name.

    cause : Name
        y for 'raise x from y'

    """
    __slots__ = ('exc', 'cause')


class Assert(StatementNode):
    """Node representing an assertion.

    Attributes
    ----------
    test : ExpressionNode
        Expression to assert.

    msg : ExpressionNode
        Message for the Assertion generally as Str node.

    """
    __slots__ = ('test', 'msg')


class Delete(StatementNode):
    """Node representing a variable deletion.

    Attributes
    ----------
    targets : list[ExpressionNode]
        Nodes to delete, generally Name, Attribute or Subscript nodes.

    """
    __slots__ = ('targets',)
    __defaults__ = {'targets': list}


class Pass(StatementNode): pass


# --- Imports

class Import(StatementNode):
    """Node representing an import.

    Attributes
    ----------
    names : list[alias]
        List of imported names.

    """
    __slots__ = ('names',)
    __defaults__ = {'names': list}


class ImportFrom(StatementNode):
    """Node representing an 'import ... from' statement.

    Attributes
    ----------
    module : unicode
        Name of the module from which values are imported, without leading dots

    names : list[alias]
        Names being imported from the module.

    level : int
        0 for absolute imports or the number of leading dots.

    """

    __slots__ = ('module', 'names', 'level')
    __defaults__ = {'names': list, 'level': int}


class alias(PyAstNode):
    """Node represeting an imported name.

    Attributes
    ----------
    name : unicode
        Name of the imported value.

    asname : unicode|None
        Aliased name (import a as b).

    """
    __slots__ = ('name', 'asname')


# --- Control flow

class If(StatementNode):
    """Node representing a if statement.

    Attributes
    ----------
    test : ExpressionNode
        Expression to test.

    body : list[PyAstNodes]
        Action to execute when the test evaluates to True.

    orelse : list[PyAstNode]
        Else or elif clauses see Notes.

    Notes
    -----
    elif clauses don’t have a special representation in the AST, but rather
    appear as extra If nodes within the orelse section of the previous one.

    """
    __slots__ = ('test', 'body', 'orelse')
    __defaults__ = {'body': list, 'orelse': list}


class While(StatementNode):
    """Node representing a while statement.

    Attributes
    ----------
    test : ExpressionNode
        Expression to test.

    body : list[PyAstNodes]
        Action to execute when the test evaluates to True.

    orelse : list[PyAstNode]
        Else clause to execute when test is never True.

    """
    __slots__ = ('test', 'body', 'orelse')
    __defaults__ = {'body': list, 'orelse': list}


class For(StatementNode):
    """Node representing a if statement.

    Attributes
    ----------
    target : Name|Tuple|List
        Variable(s) the loop assigns to.

    iter : ExpressionNode
        Items on which to loop.

    body : list[PyAstNodes]
        Nodes to execute on each iteration.

    orelse : list[PyAstNode]
        Nodes to execute if the iteration finishes normally (no break).

    """
    __slots__ = ('target', 'iter', 'body', 'orelse')
    __defaults__ = {'body': list, 'orelse': list}


class Break(StatementNode): pass
class Continue(StatementNode): pass


class Try(StatementNode):
    """Node representing a Try statement.

    Attributes
    ----------
    body : list[PyAstNode]
        Nodes to execute inside the try.

    handlers : list[ExceptHandler]
        Nodes to execute if an exception occurs.

    orelse : list[PyAstNode]
        Nodes o execute if no exception occurs.

    finalbody : list[PyAstNode]
        Nodes to always execute.

    """

    __slots__ = ('body', 'handlers', 'orelse', 'finalbody')
    __defaults__ = {'body': list, 'handlers': list, 'orelse': list,
                    'finalbody': list}


class ExceptHandler(PyAstNode):
    """Node representing an exception handling.

    Attributes
    ----------
    type : ExpressionNode|None
        Type of exception to catch or None to catch all exceptions.

    name : unicode|None
        Name used to reference the exception.

    body : list[PyAstNode]
        Nodes to execute when the exception occurs.

    """
    __slots__ = ('type', 'name', 'body')
    __defaults__ = {'body': list}


class With(StatementNode):
    """Node representing a with statement.

    Attributes
    ----------
    items : list[withitem]
        List of context managers used in the with.

    body : list[PyAstNode]
        Nodes to execute inside the with.

    """
    __slots__ = ('items', 'body')
    __defaults__ = {'items': list, 'body': list}


class withitem(PyAstNode):
    __slots__ = ('context_expr', 'optional_vars')


# --- Functions and class definitions.

class FuncDef(StatementNode):
    """Function definition node.

    Attributes
    ----------
    name : unicode
        Name of the function.

    args : arguments
        All arguments of the function.

    body : list[PyAstNode]
        Nodes to execute during a function call.

    decorator_list : list[ExpressionNode]
        List of decorators to apply on the function, generally Name or Call
        nodes.

    returns : ExpressionNode
        Return annotation.

    """
    __slots__ = ('name', 'args', 'body', 'decorator_list', 'returns')
    __defaults__ = {'decorator_list': list, 'returns': list, 'body': list}


class Lambda(ExpressionNode):
    """Lambda function creation node.

    Attributes
    ----------
    args : arguments
        All arguments of the function.

    body : ExpressionNode
        Body of the lambda function.

    """

    __slots__ = ('args', 'body')


class arguments(PyAstNode):
    """Node representing a function arguments.

    Attributes
    ----------
    args : list[arg]
        Positional arguments.

    vararg : arg
        Unpacked positional arguments.

    kwonlyargs : list[arg]
        Keyword arguments.

    kwarg : arg
        Unpacked keyword arguments.

    defaults : list
        List of default values for positional arguments.

    kw_defaults : list
        Default values for keyword arguments.

    """
    __slots__ = ('args', 'vararg', 'kwonlyargs', 'kwarg', 'defaults',
                 'kw_defaults')
    __defaults__ = {'args': list, 'kwonlyargs': list, 'defaults': list,
                    'kw_defaults': list}


class arg(PyAstNode):
    """Node representing a function argument.

    Attribute
    ---------
    arg : unicode
        Name of the argument.

    annotation : ExpressionNode|None
        Annotation of the argument, generally a Str or Name node.

    """
    __slots__ = ('arg', 'annotation')


class Returns(StatementNode):
    """Node representing a return statement.

    Attributes
    ----------
    value : ExpressionNode
        Value to return.

    """
    __slots__ = ('value',)


class Yield(ExpressionNode):
    """Node representing a yield statement.

    Attributes
    ----------
    value : ExpressionNode
        Value to yield.

    """
    __slots__ = ('value',)


class YieldFrom(ExpressionNode):
    """Node representing a yield from statement.

    Attributes
    ----------
    value : ExpressionNode
        iterator to yield.

    """
    __slots__ = ('value',)


class Global(ExpressionNode):
    __slots__ = ('names',)
    __defaults__ = {'names': list}


class NonLocal(ExpressionNode):
    __slots__ = ('names',)
    __defaults__ = {'names': list}


class ClassDef(StatementNode):
    """Class definition node.

    Attributes
    ----------
    name : unicode
        Name of the class.

    bases : list[ExpressionNode]
        List of base classes.

    keywords : list[keyword]
        Metaclass and arguments to pass to the metaclass.

    body : list[PyAstNode]
        Body of the class definition.

    decorator_list : list[ExpressionNode]
        List of decorators to apply on the function, generally Name or Call
        nodes.

    """

    __slots__ = ('name', 'bases', 'keywords', 'body', 'decorator_list')
    __defaults__ = {'bases': list, 'keywords': list, 'body': list,
                    'decorator_list': list}


class Module(PyAstNode):
    """node representing a python module.

    """
    __slots__ = ('body')
    __defaults__ = {'body': list}


BASETYPE_MAP = {
    int: Int,
    type(''): Str,
    float: Float,
    tuple: Tuple,
    dict: Dict,
    list: List,
    set: Set,
    slice: Slice,
}
