# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""This module contains a AST classes for python code.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from pyclibrary.asts.astcore import AstNode


class PyAstNode(AstNode): pass

class Statement(PyAstNode): pass
class IfStmt(Statement): __slots__ = ('condition', 'then_blk', 'else_blk')
class WhileStmt(Statement): __slots__ = ('condition', 'loop_blk')
class ForStmt(Statement): __slots__ = ('var_name', 'iter_expr', 'loop_blk')
class TryStmt(Statement):
    __slots__ = ('try_blk', 'excepts', 'else_blk', 'finally_blk')
class Except(PyAstNode): __slots__ = ('exc_cls', 'var_name', 'except_blk')

class Expression(AstNode): pass
class Id(Expression): __slots__ = ('name',)
class Parens(Expression): __slots__ = ('expr')
class Item(Expression): __slots__ = ('expr', 'ndx_expr')

class Call(Expression):

    __slots__ = ('expr', 'args_list', 'argv_list')

    def __init__(self, expr, args_list=None, argv_list=None):
        super(Call, self).__init__()
        self.expr = expr
        self.args_list = args_list or ()
        self.argv_list = argv_list or ()


class Assign(Statement):
    OP_STR = '='
    __slots__ = ('var', 'expr')

class AssignAdd(Assign): OP_STR = '+='
class AssignSub(Assign): OP_STR = '-='
class AssignMul(Assign): OP_STR = '*='
class AssignDiv(Assign): OP_STR = '/='
# todo: add all missing assign ops

class UnnaryOp(Expression):
    OP_STR = None
    __slots__ = ('expr',)

class BinaryOp(Expression):
    OP_STR = None
    __slots__ = ('expr1', 'expr2')

class Attr(BinaryOp): OP_STR = '.'
class Add(BinaryOp): OP_STR = '+'
class Sub(BinaryOp): OP_STR = '-'
class Mul(BinaryOp): OP_STR = '*'
class Div(BinaryOp): OP_STR = '/'
# todo: add all missing binary ops

class Const(Expression): pass
class Int(Const): __slots__ = ('int_val',)
class Str(Const): __slots__ = ('str_val',)
class Float(Const): __slots__ = ('float_val')
class Tuple(Const): __slots__ = ('init_list',)
class Dict(Const): __slots__ = ('init_list',)
class List(Const): __slots__ = ('init_list',)
class Set(Const): __slots__ = ('init_list',)
class Slice(Const): __slots__ = ('start', 'stop', 'step')


class FuncDef(Statement):

    __slots__ = ('name', 'param_name_list', 'default_dict', 'decorator_list',
                 'param_anot_dict', 'func_anot_expr')

    # define defaults for most parameters
    def __init__(self, name, param_name_list=(), default_dict={},
                 decorator_list=(), param_anot_dict={}, func_anot_expr=None):
        super(FuncDef, self).__init__()
        self.name = name
        self.param_name_list = param_name_list
        self.default_dict = default_dict
        self.decorator_list = decorator_list
        self.param_anot_dict = param_anot_dict
        self.func_anot_expr = func_anot_expr


class ClassDef(Statement):

    __slots__ = ('name', 'parent_class_list', 'statement_list',
                 'decorator_list', 'metacls')

    # define defaults for most parameters
    def __init__(self, name, parent_class_list=(), statement_list=(),
                 decorator_list=(), metacls=None):
        super(ClassDef, self).__init__()
        self.name = name
        self.parent_class_list = parent_class_list
        self.statement_list = statement_list
        self.decorator_list = decorator_list
        self.metacls = metacls


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
