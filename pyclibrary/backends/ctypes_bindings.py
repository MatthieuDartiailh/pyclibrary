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
from ..asts.astcore import Transformer
from pyclibrary.asts import c as c
from ..asts import python as py


class CTypesBindingsCreator(Transformer):

    BUILDINTYPE_MAP = {
        'bool': 'c_bool',
        'char': 'c_char',
        'wchar': 'c_wchar',
        'unsigned char': 'c_ubyte',
        'short': 'c_short',
        'short int': 'c_short',
        'unsigned short': 'c_ushort',
        'unsigned short int': 'c_ushort',
        'int': 'c_int',
        'unsigned': 'c_uint',
        'unsigned int': 'c_uint',
        'long': 'c_long',
        'long int': 'c_long',
        'unsigned long': 'c_ulong',
        'unsigned long int': 'c_ulong',
        'long long': 'c_longlong',
        'long long int': 'c_longlong',
        'unsigned __int64': 'c_ulonglong',
        'unsigned long long': 'c_ulonglong',
        'unsigned long long int': 'c_ulonglong',
        'float': 'c_float',
        'double': 'c_double',
        'long double': 'c_longdouble',
        'uint8_t': 'c_uint8',
        'int8_t': 'c_int8',
        'uint16_t': 'c_uint16',
        'int16_t': 'c_int16',
        'uint32_t': 'c_uint32',
        'int32_t': 'c_int32',
        'uint64_t': 'c_uint64',
        'int64_t': 'c_int64'
    }

    def __init__(self, dllobj_name='_dll'):
        super(CTypesBindingsCreator, self).__init__()
        self.dllobj_name = dllobj_name

    def transform_clib_interface(self, clib):
        for name, c_ast in clib.vars.items():
            yield py.Assign(
                py.Id(name),
                py.Call(
                    py.Attr(self(c_ast), 'in_dll'),
                    [self.dllobj_name, py.Str(name)]))

    @Transformer.register(c.ValMacro)
    def transformValMacro(self, ast, name):
        try:
            contentVal = eval(ast.content)
        except Exception:
            pass
        else:
            if isinstance(contentVal, type('')):
                contentAstType = py.BASETYPE_MAP[type(contentVal)]
                yield py.Assign(py.Id(name), contentAstType(contentVal))

    @Transformer.register(c.BuiltinType)
    def transformBuildinType(self, ast):
        ctypes_type = self.BUILDINTYPE_MAP[ast.type_name]
        yield py.Id(ctypes_type)

    @Transformer.register(c.PointerType)
    def transformPointerType(self, ast):
        yield py.Call(py.Id('POINTER'), [self(ast.base_type)])
