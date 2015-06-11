# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test cm.py via pytest
"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
import pytest
from pyclibrary import c_model as cm


class TestCLibBase(object):

    class DummyType(cm.CLibBase):

        __slots__ = ['p1', 'p2', 'p3', 'p4']

        def __init__(self, p1, p2, p3=None, p4=None):
            super(TestCLibBase.DummyType, self).__init__()
            self.p1 = p1
            self.p2 = p2
            self.p3 = p3
            self.p4 = p4

    def test_repr(self):
        def assert_repr_valid(expr_str):
            assert (repr(eval(expr_str, {'DummyType': self.DummyType})) ==
                    expr_str)
        assert_repr_valid("DummyType(3, [{!r}, {!r}])".format('tst', 'tst2'))
        assert_repr_valid("DummyType(0, [], p3={!r})".format('Test'))
        assert_repr_valid("DummyType(0, [], p4=[2, 3])")
        assert_repr_valid("DummyType(0, [], p3={!r}, p4=[2, 3])"
                          .format('Test'))

    def test_eq(self):
        assert self.DummyType(0, []) == self.DummyType(0, [])
        assert (self.DummyType(3, ['test', 'test2'], 'test3', [9]) ==
                self.DummyType(3, ['test', 'test2'], 'test3', [9]))

        assert self.DummyType(0, []) != self.DummyType(1, [])
        assert self.DummyType(0, []) != self.DummyType(0, ['test'])
        assert self.DummyType(0, []) != self.DummyType(0, [], p3='test')
        assert self.DummyType(0, []) != self.DummyType(0, [], p4=[])

        class OtherDummyType(cm.CLibType):
            def c_repr(self, inner=None):
                return ''
        assert self.DummyType(0, []) != OtherDummyType()

    def test_copy(self):
        orig_obj = self.DummyType(3, ['test'], 'test2', [9])
        copied_obj = orig_obj.copy()
        assert orig_obj == copied_obj
        assert orig_obj is not copied_obj
        assert orig_obj.p1 is copied_obj.p1


class TestCLibType(object):

    class DummyType(cm.CLibType):

        def c_repr(self, inner=None):
            return "dummy<{!r}>".format(inner)

    def test_str(self):
        assert str(self.DummyType()) == "dummy<None>"

    def test_resolve(self):
        dummy_type = self.DummyType(['tq2'])
        assert dummy_type.resolve({}) == dummy_type


class TestSimpleType(object):

    def test_c_repr(self):
        assert cm.SimpleType('char').c_repr() == 'char'
        assert cm.SimpleType('any text _123').c_repr() == 'any text _123'
        assert cm.SimpleType('char').c_repr('a') == 'char a'
        qual_type = cm.SimpleType('unsigned char', quals=['tp1', 'tp2'])
        assert qual_type.c_repr() == 'tp1 tp2 unsigned char'
        assert qual_type.c_repr('a') == 'tp1 tp2 unsigned char a'


class TestCustomType(object):

    def test_resolve(self):
        simple_type = cm.BuiltinType('char')
        typedefs = {'simple': simple_type,
                    'nestedtype': cm.CustomType('simple'),
                    'qualtype': cm.BuiltinType('char', quals=['tq2'])}

        assert cm.CustomType('simple').resolve(typedefs) is simple_type
        assert cm.CustomType('nestedtype').resolve(typedefs) is simple_type
        assert (cm.CustomType('qualtype', quals=['tq1']).resolve(typedefs) ==
                cm.BuiltinType('char', quals=['tq1', 'tq2']))

        with pytest.raises(cm.UnknownCustomType):
            cm.CustomType('unknowntype').resolve(typedefs)


class TestStructType(object):

    def test_init(self):
        with pytest.raises(ValueError):
            cm.StructType([], packsize=3)    # packsize != 2^n

    def test_c_repr(self):
        simple_fields = [('field', cm.BuiltinType('int'))]

        assert (cm.StructType(simple_fields).c_repr() ==
                "struct {\n"
                "    int field;\n"
                "}")

        _2_fields = [('f1', cm.BuiltinType('int')),
                     ('f2', cm.BuiltinType('signed short'))]
        assert (cm.StructType(_2_fields).c_repr('struct struct_name_t') ==
                "struct struct_name_t {\n"
                "    int f1;\n"
                "    signed short f2;\n"
                "}")

        assert (cm.StructType(simple_fields, packsize=2).c_repr() ==
                "#pragma pack(push, 2)\n"
                "struct {\n"
                "    int field;\n"
                "}\n"
                "#pragma pack(pop)\n")
        assert (cm.StructType(simple_fields, quals=['tp1', 'tp2']).c_repr() ==
                "tp1 tp2 struct {\n"
                "    int field;\n"
                "}")

        with pytest.raises(ValueError):
            cm.StructType(simple_fields).c_repr('missing_struct_keyword')


class TestBitFieldType(object):

    def test_c_repr(self):
        simple_lst = [('field', cm.BuiltinType('int'), 4)]
        assert (cm.BitFieldType(simple_lst).c_repr() ==
                "struct {\n"
                "    int field : 4;\n"
                "}")


class TestUnionType(object):

    def test_c_repr(self):
        simple_fields = [('field', cm.BuiltinType('int'))]
        assert (cm.UnionType(simple_fields).c_repr() ==
                "union {\n"
                "    int field;\n"
                "}")

        with pytest.raises(ValueError):
            cm.UnionType(simple_fields).c_repr('missing_union_keyword')


class TestEnumType(object):

    def test_c_repr(self):
        simple_lst = [('val1', 3), ('val2', 99)]
        assert (cm.EnumType(simple_lst, ['tq1', 'tq2']).c_repr('enum enm_') ==
                "tq1 tq2 enum enm_ {\n"
                "    val1 = 3,\n"
                "    val2 = 99,\n"
                "}")

        with pytest.raises(ValueError):
            cm.EnumType(simple_lst).c_repr('missing_enum_keyword')


class TestPointerType(object):

    def test_c_repr(self):
        assert cm.PointerType(cm.BuiltinType('int')).c_repr() == 'int *'
        assert (cm.PointerType(cm.BuiltinType('int')).c_repr('name') ==
                'int * name')
        assert (cm.PointerType(cm.BuiltinType('int', quals=['tq1']),
                               quals=['tq2']).c_repr('name') ==
                'tq1 int * tq2 name')

        assert (cm.PointerType(cm.PointerType(cm.BuiltinType('int')))
                .c_repr() ==
                'int * *')

    def test_resolve(self):
        simple_type = cm.BuiltinType('int')
        typedefs = {'simple': simple_type,
                    'ptr': cm.PointerType(cm.CustomType('simple'))}
        simple_ptr = cm.PointerType(simple_type)

        assert simple_ptr is simple_ptr
        assert (cm.PointerType(cm.CustomType('simple')).resolve(typedefs) ==
                cm.PointerType(simple_type))
        assert (cm.PointerType(cm.CustomType('simple'), quals=['tq'])
                .resolve(typedefs) ==
                cm.PointerType(simple_type, quals=['tq']))

        assert (cm.PointerType(cm.PointerType(cm.CustomType('simple')))
                .resolve(typedefs) ==
                cm.PointerType(cm.PointerType(simple_type)))
        assert (cm.PointerType(cm.CustomType('ptr')).resolve(typedefs) ==
                cm.PointerType(cm.PointerType(simple_type)))


class TestArrayType(object):

    def test_init(self):
        with pytest.raises(ValueError):
            cm.ArrayType(cm.BuiltinType('int'), quals=['tq'])

    def test_c_repr(self):
        int_type = cm.BuiltinType('int')
        assert cm.ArrayType(int_type).c_repr() == 'int []'
        assert cm.ArrayType(int_type, 4).c_repr() == 'int [4]'
        assert cm.ArrayType(int_type, 99).c_repr('name') == 'int name[99]'

        assert (cm.ArrayType(cm.ArrayType(int_type, 1), 2).c_repr() ==
                'int [2][1]')

        assert (cm.ArrayType(cm.PointerType(int_type)).c_repr('name') ==
                'int * name[]')
        assert (cm.PointerType(cm.ArrayType(int_type)).c_repr('name') ==
                'int (* name)[]')


class TestFunctionType(object):

    def test_return_type(self):
        ret_type = cm.BuiltinType('int')
        assert cm.FunctionType(ret_type, []).return_type == ret_type

    def test_c_repr(self):
        int_type = cm.BuiltinType('int')
        assert cm.FunctionType(int_type, []).c_repr('f') == 'int f()'
        assert (cm.FunctionType(int_type, [('a', int_type), (None, int_type)])
                .c_repr('f') ==
                'int f(int a, int)')
        assert (cm.PointerType(cm.FunctionType(int_type, [])).c_repr() ==
                'int (*)()')
        assert (cm.FunctionType(cm.PointerType(int_type), []).c_repr('f') ==
                'int * f()')

        with pytest.raises(ValueError):
            # anonymous functions are not valid C constructs
            cm.FunctionType(int_type, []).c_repr()


class TestMacro(object):

    def test_c_repr(self):
        assert (cm.Macro('content').c_repr('name') ==
                '#define name content\n')
        assert (str(cm.Macro('content')) ==
                '#define ? content\n')


class TestFnMacro(object):

    def test_c_repr(self):
        assert (cm.FnMacro('a + b + c', ['a', 'b']).c_repr('name') ==
                '#define name(a, b) a + b + c\n')


class TestCLibInterface(object):

    @pytest.fixture
    def clib(self):
        return cm.CLibInterface()

    def test_add_func(self, clib):
        clib.add_func('f', cm.FunctionType(cm.BuiltinType('int'), []),
                      'header.h')
        assert clib.file_map['f'] == 'header.h'
        assert clib.funcs == {'f': cm.FunctionType(cm.BuiltinType('int'), [])}
        assert clib.vars == {}
        assert clib == {'f': cm.FunctionType(cm.BuiltinType('int'), [])}

    def test_add_var(self, clib):
        clib.add_var('v', cm.BuiltinType('int'), 'header.h')
        assert clib.file_map['v'] == 'header.h'
        assert clib.vars == {'v':cm.BuiltinType('int')}
        assert clib.funcs == {}
        assert clib == {'v': cm.BuiltinType('int')}

    def test_add_typedef(self, clib):
        clib.add_typedef('t', cm.BuiltinType('int'), 'header.h')
        assert clib.file_map['t'] == 'header.h'
        assert clib.typedefs == {'t':cm.BuiltinType('int')}
        assert clib.funcs == {}
        assert clib == {'t': cm.BuiltinType('int')}

    def test_add_macro(self, clib):
        clib.add_macro('m', cm.Macro('1'), 'header.h')
        assert clib.file_map['m'] == 'header.h'
        assert clib.macros == {'m':cm.Macro('1')}
        assert clib.funcs == {}
        assert clib == {'m': cm.Macro('1')}
