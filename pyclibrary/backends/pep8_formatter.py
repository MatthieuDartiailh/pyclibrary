# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Provides a function for layouting a python AST in PEP8 style.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from pyclibrary.asts import python as py
from pyclibrary.asts.astcore import Transformer


class Pep8Formatter(Transformer):
    """creates the text representation of 'pyAst' with the help of 'layouter'.
    """
    
    def __init__(self, layouter, flavour='py3'):
        """formats python ast according to pep8
        
        Parameters
        ----------
        layouter : CodeLayouter
            The layout engine that is used to write the output
    
        flavour : str [optional]
            Specifies the exact syntax flavour of the outputted text.
            Has to be one of 'py2', 'py3', 'six', 'future'
    
        """
        super(Pep8Formatter, self).__init__()
        self.layouter = layouter
        self.flavour = flavour


    @Transformer.register(py.Id)
    def idFormat(self, ast):
        self.layouter.tokens(ast.name)
    

    @Transformer.register(py.Str)
    def strFormat(self, ast):
        self.layouter.tokens(repr(ast.str_val))


    @Transformer.register(py.Int)
    def intFormat(self, ast):
        self.layouter.tokens(repr(ast.int_val))


    @Transformer.register(py.BinaryOp)
    def binaryOpFormat(self, ast):
        self.transform(ast.expr1)
        self.layouter.space().tokens(ast.OP_STR).space()
        self.transform(ast.expr2)
    
    
    @Transformer.register(py.Assign)
    def assignFormat(self, ast):
        self.transform(ast.var)
        self.layouter.space().tokens(ast.OP_STR).space()
        self.transform(ast.expr)


    @Transformer.register(py.ClassDef)
    def classDefFormat(self, ast):
        self.layouter.min_vdist(2)
        self.layouter.tokens('class').space()
        if len(ast.parent_class_list) == 0:
            self.layouter.tokens(ast.name+':').nl()
        else:
            self.layouter.tokens(ast.name+'(')
            for additional_class in ast.parent_class_list[:-1]:
                self.transform(additional_class)
                self.layouter.tokens(',').space()
            self.transform(ast.parent_class_list[-1])
            self.layouter.tokens('):').nl()
        with self.layouter.layout(rel_indent=4):
            if len(ast.statement_list) == 0:
                self.layouter.tokens('pass')
            else:
                for statement in ast.statement_list:
                    self.layouter.min_vdist(1)
                    self.transform(statement)
                    self.layouter.min_vdist(1)
        self.layouter.min_vdist(2)
