# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""
Proxy to both CHeader and ctypes, allowing automatic type conversion and
function calling based on C header definitions.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from pyclibrary.backends.ctypes_bindings import  CTypesBindingsCreator
from pyclibrary.asts import astcore
from pyclibrary.asts import c
from pyclibrary.asts import python as py


class TestCTypesBindingsCreator(object):

    def assert_transform(self, cAst, ctx, *pyAst):
        ctbCreator = CTypesBindingsCreator()
        result = ctbCreator.transform(cAst, *ctx)
        assert list(astcore.flatten(result)) == list(pyAst)

    def assert_transform_clib_interface(self, cAst, *pyAst):
        ctbCreator = CTypesBindingsCreator('test_dll')
        result = ctbCreator.transform_clib_interface(cAst)
        assert list(astcore.flatten(result)) == list(pyAst)

    def test_valMacro(self):
        self.assert_transform(
            c.ValMacro('"test"'), ('name',),
            py.Assign(py.Id('name'), py.Str("test")))

    def test_buildIntType(self):
        self.assert_transform(
            c.BuiltinType('unsigned int'), (),
            py.Id('c_uint'))

    def test_pointerType(self):
        self.assert_transform(
            c.PointerType(c.BuiltinType('int')), (),
            py.Call(py.Id('POINTER'), [py.Id('c_int')]))

    def test_transformCLibInterface_onVars(self):
        clib = c.CLibInterface()
        clib.add_var('test', c.BuiltinType('int'))
        self.assert_transform_clib_interface(
            clib,
            py.Assign(
                py.Id('test'),
                py.Call(
                    py.Attr(py.Id('c_int'), 'in_dll'),
                    ['test_dll', py.Str('test')])))