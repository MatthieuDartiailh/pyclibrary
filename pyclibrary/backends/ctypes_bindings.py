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

    BUILTINTYPE_MAP = {
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

    BUILTINPOINTERTYPE_MAP = {
        'char': 'c_char_p',
        'wchar': 'c_wchar_p',
        'wchar_t': 'c_wchar_p',
        'void': 'c_void_p'
    }

    def __init__(self, dllobj_name='_dll'):
        super(CTypesBindingsCreator, self).__init__()
        self.dllobj_name = dllobj_name
        self._clib = None

    def transform_clib_interface(self, clib):
        """Turn a CLib AST object into one or several python modules.

        """
        self._clib = clib
        # By adding Module to the python ast we could easily generate
        # Multiple files for different kind of values.
        for name, c_ast in clib.vars.items():
            yield py.Assign(
                py.Id(name),
                py.Call(
                    py.Attr(self(c_ast), 'in_dll'),
                    [self.dllobj_name, py.Str(name)]))

    @Transformer.register(c.ValMacro)
    def transform_val_macro(self, ast, name):
        """Create an assignement binding the macro name to its value.

        """
        content_val = ast.value if ast.value is not None else ast.content
        contentAstType = py.BASETYPE_MAP[type(content_val)]
        yield py.Assign(py.Id(name), contentAstType(content_val))

    @Transformer.register(c.BuiltinType)
    def transform_buildin_type(self, ast):
        """Turn a buildin type into its associated ctype type.

        """
        ctypes_type = self.BUILTINTYPE_MAP[ast.type_name]
        yield py.Id(ctypes_type)

    @Transformer.register(c.CustomType)
    def transform_custom_type(self, ast):
        """Turn a custom type into a custom ctype declaration.

        """
        typ = ast.resolve(self._clib.typedefs)
        yield self(typ)

    @Transformer.register(c.PointerType)
    def transform_pointer_type(self, ast):
        """Turn a pointer type into the equivalent ctype construct.

        """
        if (isinstance(ast.base_type, c.BuiltinType) and
                ast.base_type.type_name in self.BUILTINPOINTERTYPE_MAP):
            yield py.Id(self.BUILTINPOINTERTYPE_MAP[ast.base_type.type_name])
        else:
            yield py.Call(py.Id('POINTER'), [self(ast.base_type)])
