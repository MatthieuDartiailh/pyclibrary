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
from ..asts.astcore import Transformer, flatten
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

    def transform_clib_interface(self, clib):
        """Turn a CLib AST object into one or several python modules.

        """
        ctx = {'clib': clib}
        # By adding Module to the python ast we could easily generate
        # Multiple files for different kind of values.
        statements = (self.make_imports(ctx),
                      self.build_clib_class(ctx))
        yield py.Module(body=flatten(statements))

    def make_imports(self, ctx):
        """Build the necessary imports for the clibrary module to run.

        """
        yield py.Import(names=[py.alias(name='ctypes', asname='ct')])
        yield py.ImportFrom()  # base classes imports
        yield py.ImportFrom()  # utility function imports

    def build_clib_class(self, ctx):
        """
        """
        statements = []
        for n, m in ctx['clib'].macros:



    @Transformer.register(c.ValMacro)
    def transform_val_macro(self, ast, ctx):
        """Create an assignement binding the macro name to its value.

        """
        name = ctx['name']
        clib = ctx['clib']
        if name in clib.macro_vals:
            content_val = clib.macro_vals[name]
        else:
            content_val = ast.content
        content_ast_type = py.BASETYPE_MAP[type(content_val)]
        # XXXX handle prefix
        yield py.Assign(targets=[py.Name(id=name, ctx=py.Store())],
                        value=content_ast_type(content_val))

    @Transformer.register(c.FnMacro)
    def transform_fun_macro(self, ast, ctx):
        """Skip function macro as they are not exported by the dll.

        """
        yield

    @Transformer.register(c.BuiltinType)
    def transform_buildin_type(self, ast, ctx):
        """Turn a buildin type into its associated ctype type.

        """
        ctypes_type = self.BUILTINTYPE_MAP[ast.type_name]
        yield py.Name(id=ctypes_type, ctx=py.Load())

    @Transformer.register(c.CustomType)
    def transform_custom_type(self, ast, ctx):
        """Turn a custom type into a custom ctype declaration.

        """
        typ = ast.resolve(ctx['clib'].typedefs)
        yield self(typ, ctx)

    @Transformer.register(c.PointerType)
    def transform_pointer_type(self, ast):
        """Turn a pointer type into the equivalent ctype construct.

        """
        # Handle char pointer and void pointers.
        if (isinstance(ast.base_type, c.BuiltinType) and
                ast.base_type.type_name in self.BUILTINPOINTERTYPE_MAP):
            yield py.Name(self.BUILTINPOINTERTYPE_MAP[ast.base_type.type_name])

        # Handle double pointer void
        elif (isinstance(ast.base_type, c.PointerType) and
                isinstance(ast.base_type.base_type, c.BuiltinType) and
                ast.base_type.base_type.type_name == 'void'):
            yield py.Name(self.BUILTINPOINTERTYPE_MAP['voip'])

        else:
            yield py.Call(py.Name('POINTER'), [self(ast.base_type)])

    @Transformer.register(c.ArrayType)
    def transform_array_type(self, ast):
        """Turn an array type into the equivalent ctype construct.

        """
        if ast.size is None:
            yield py.Call(py.Name('POINTER'), [self(ast.base_type)])
        else:
            yield py.BinaryOp(self(ast.base_type), py.Mul, py.Int(ast.size))
