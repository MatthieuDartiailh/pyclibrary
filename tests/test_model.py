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

    def test_with_quals(self):
        type_ = self.DummyType(['x'])
        assert type_.with_quals(['y']) == self.DummyType(['x', 'y'])
        assert type_ == self.DummyType(['x'])
        assert type_.with_quals([]) is type_

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
                    'qualtype': cm.BuiltinType('char', quals=['tq2']),
                    'cyclictype': cm.CustomType('cyclictype')}

        assert cm.CustomType('simple').resolve(typedefs) is simple_type
        assert cm.CustomType('nestedtype').resolve(typedefs) is simple_type
        assert (cm.CustomType('qualtype', quals=['tq1']).resolve(typedefs) ==
                cm.BuiltinType('char', quals=['tq2', 'tq1']))

        with pytest.raises(cm.UnknownCustomTypeError):
            cm.CustomType('unknowntype').resolve(typedefs)
        with pytest.raises(cm.UnknownCustomTypeError):
            cm.CustomType('cyclictype').resolve(typedefs)


class TestStructType(object):

    def test_init(self):
        with pytest.raises(ValueError):
            cm.StructType([], packsize=3)    # packsize != 2^n

    def test_c_repr(self):
        simple_field = ('field', cm.BuiltinType('int'), None)

        assert (cm.StructType([simple_field]).c_repr() ==
                "struct {\n"
                "    int field;\n"
                "}")

        second_field = ('field2', cm.BuiltinType('signed short'), None)
        assert (cm.StructType([simple_field, second_field])
                .c_repr('struct struct_name_t') ==
                "struct struct_name_t {\n"
                "    int field;\n"
                "    signed short field2;\n"
                "}")

        assert (cm.StructType([simple_field], packsize=2).c_repr() ==
                "#pragma pack(push, 2)\n"
                "struct {\n"
                "    int field;\n"
                "}\n"
                "#pragma pack(pop)\n")

        bit_field = ('field', cm.BuiltinType('int'), 4)
        assert (cm.StructType([bit_field]).c_repr() ==
                "struct {\n"
                "    int field : 4;\n"
                "}")

        anonn_field = (None, cm.CustomType('struct s'), None)
        assert (cm.StructType([anonn_field]).c_repr() ==
                "struct {\n"
                "    struct s;\n"
                "}")

        with pytest.raises(ValueError):
            cm.StructType([simple_field]).c_repr('missing_struct_keyword')


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

    def test_init(self):
        with pytest.raises(ValueError):
            cm.EnumType([('val', 1)], quals=['keyword'])

    def test_c_repr(self):
        simple_lst = [('val1', 3), ('val2', 99)]
        assert (cm.EnumType(simple_lst).c_repr('enum enm_') ==
                "enum enm_ {\n"
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
                    'ptr': cm.PointerType(cm.CustomType('simple')),
                    'cycle': cm.PointerType(cm.CustomType('cycle'))}
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

        with pytest.raises(cm.UnknownCustomTypeError):
            cm.CustomType('cycle').resolve(typedefs)


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
        assert str(cm.FunctionType(int_type, [])) == 'int <<funcname>>()'


class TestMacro(object):

    def test_c_repr(self):
        macro = cm.ValMacro('content')
        assert (macro.c_repr('name') == '#define name content')
        assert (str(macro) == '#define <<macroname>> content')

    def test_content(self):
        content = 'int f() { return(0); }'
        assert cm.ValMacro(content).content == content


class TestFnMacro(object):

    def test_repr(self):
        assert (repr(cm.FnMacro('a1 + b2', ['a1', 'b2'])) ==
                'FnMacro({!r}, [{!r}, {!r}])'.format('a1 + b2', 'a1', 'b2'))

    def test_c_repr(self):
        macro = cm.FnMacro('a + b + c', ['a', 'b'])
        assert (macro.c_repr('name') == '#define name(a, b) a + b + c')
        assert (str(macro) == '#define <<macroname>>(a, b) a + b + c')

    def test_content(self):
        content = 'RTYPE f() {printf("%i", RVAL); return(RVAL+rval);}'
        macro = cm.FnMacro(content, ['RTYPE', 'RVAL'])
        assert macro.content == content
        assert (macro.compiled_content ==
                '{RTYPE} f() {{printf("%i", {RVAL}); return({RVAL}+rval);}}')
        assert (macro.parametrized_content('int', '3') ==
                'int f() {printf("%i", 3); return(3+rval);}')
        assert (macro.parametrized_content(RVAL='4', RTYPE='char') ==
                'char f() {printf("%i", 4); return(4+rval);}')
        assert (macro.parametrized_content('short', RVAL='5') ==
                'short f() {printf("%i", 5); return(5+rval);}')
        with pytest.raises(TypeError):
            macro.parametrized_content('int', '3', RTYPE='char')


class TestCLibInterface(object):

    @pytest.fixture
    def clib(self):
        return cm.CLibInterface()

    def assert_add_obj(self, clib, obj_map, add_func, obj_type,
                       other_obj_type=None):
        add_func('objname', obj_type, 'header.h')

        # check if added to all required dicts
        assert obj_map == {'objname': obj_type}
        for other_map in clib.obj_maps.values():
            if other_map != obj_map:
                assert other_map == {}
        assert clib == {'objname': obj_type}
        assert clib.file_map['objname'] == 'header.h'

        # check second element
        add_func('objname2', other_obj_type, 'header.h')
        assert obj_map == {'objname': obj_type, 'objname2': other_obj_type}

    def test_add_func(self, clib):
        self.assert_add_obj(clib, clib.funcs, clib.add_func,
                            cm.FunctionType(cm.BuiltinType('int'), []),
                            cm.FunctionType(cm.BuiltinType('void'), []))

    def test_add_var(self, clib):
        self.assert_add_obj(clib, clib.vars, clib.add_var,
                            cm.BuiltinType('int'),
                            cm.BuiltinType('char'))

    def test_add_typedef(self, clib):
        self.assert_add_obj(clib, clib.typedefs, clib.add_typedef,
                            cm.BuiltinType('int'),
                            cm.BuiltinType('char'))

    def test_add_typedef_with_enum(self, clib):
        clib.add_typedef('enum x', cm.EnumType([('val1', 0), ('val2', 1)]),
                         'header.h')
        assert 'enum x' in clib.typedefs
        assert clib.enums['val1'] == 0
        assert clib.enums['val2'] == 1
        assert clib.file_map['val1'] == 'header.h'

    def test_add_macro(self, clib):
        self.assert_add_obj(clib, clib.macros, clib.add_macro,
                            cm.ValMacro('content'),
                            cm.ValMacro('othercontent'))

    def test_include(self):
        clib = cm.CLibInterface()
        clib.add_func('f', cm.FunctionType(cm.BuiltinType('int'), []), 'hd.h')
        clib.add_var('v', cm.BuiltinType('int'), 'hd.h')
        clib.add_typedef('t', cm.BuiltinType('int'), 'hd.h')
        clib.add_typedef('e', cm.EnumType([('v1', 1)]), 'hd.h')
        clib.add_macro('m', cm.ValMacro('3'), 'hd.h')

        clib2 = cm.CLibInterface()
        clib2.add_func('f2', cm.FunctionType(cm.BuiltinType('char'), []),
                       'hd2.h')
        clib2.add_var('v2', cm.BuiltinType('char'), 'hd2.h')
        clib2.add_typedef('t2', cm.BuiltinType('char'), 'hd2.h')
        clib2.add_typedef('e2', cm.EnumType([('v2', 2)]), 'hd2.h')
        clib2.add_macro('m2', cm.ValMacro('4'), 'hd2.h')

        clib.include(clib2)

        assert clib.funcs == {
            'f': cm.FunctionType(cm.BuiltinType('int'), []),
            'f2': cm.FunctionType(cm.BuiltinType('char'), [])}
        assert clib.vars == {
            'v': cm.BuiltinType('int'),
            'v2': cm.BuiltinType('char')}
        assert clib.typedefs == {
            't': cm.BuiltinType('int'),
            'e': cm.EnumType([('v1', 1)]),
            't2': cm.BuiltinType('char'),
            'e2': cm.EnumType([('v2', 2)])
        }
        assert clib.enums == {'v1': 1, 'v2': 2}
        assert clib.macros == {
            'm': cm.ValMacro('3'),
            'm2': cm.ValMacro('4')}
        assert clib.file_map['f'] == 'hd.h'
        assert clib.file_map['f2'] == 'hd2.h'
