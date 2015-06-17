# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test parser functionalities.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

import os
import sys
from pytest import raises
from pyclibrary.c_parser import CParser, Type, Struct, Union, Enum
import pyclibrary.utils
import pyclibrary.c_model as cm


H_DIRECTORY = os.path.join(os.path.dirname(__file__), 'headers')


def compare_lines(lines, lines2):
    """Compare lines striped from whitespaces characters.

    """
    for l, l_test in zip(lines, lines2):
        assert l.strip() == l_test.strip()


class TestType(object):

    def test_init(self):
        with raises(ValueError):
            Type('int', '*', type_quals=(('volatile',),))

    def test_tuple_equality(self):
        assert Type('int') == ('int',)
        assert ('int',) == Type('int')

        assert Type('int', '*', type_quals=[['const'], ['volatile']]) == \
               ('int', '*')

        assert issubclass(Type, tuple)

    def test_Type_equality(self):
        assert Type('int', '*', type_quals=(('const',), ('volatile',))) == \
               Type('int', '*', type_quals=(('const',), ('volatile',)))
        assert Type('int', '*', type_quals=(('const',), ())) != \
               Type('int', '*', type_quals=(('const',), ('volatile',)))

    def test_getters(self):
        assert Type('int', '*').type_spec == 'int'
        assert Type('int', '*', [1]).declarators == ('*', [1])
        assert Type('int', '*', type_quals=(('volatile',), ())).type_quals == \
               (('volatile',), ())

    def test_is_fund_type(self):
        assert not Type('custom_typedef').is_fund_type()

        assert Type('int').is_fund_type()
        assert Type('int', '*').is_fund_type()
        assert Type('int', [1]).is_fund_type()
        assert Type('int', ()).is_fund_type()
        assert Type('int', type_quals=(('volatile',))).is_fund_type()

        assert Type('unsigned').is_fund_type()
        assert Type('short').is_fund_type()
        assert Type('unsigned short int').is_fund_type()
        assert Type('struct test').is_fund_type()

    def test_eval(self):
        type_map = {
            'tq_parent_type': Type('int', '*',
                                   type_quals=(('__tq1',), ('__tq2',))),
            'parent_type': Type('int', '*', '*', [2]),
            'child_type': Type('parent_type', '*', [3]) }

        assert Type('parent_type', '*', [1]).eval(type_map) == \
               Type('int', '*', '*', [2], '*', [1])
        assert Type('child_type', (), '*').eval(type_map) == \
               Type('int', '*', '*', [2], '*', [3], (), '*')
        assert Type('tq_parent_type', [1],
                    type_quals=(('__tq3',), ('__tq4',))).eval(type_map) == \
               Type('int', '*', [1],
                    type_quals=(('__tq1',), ('__tq2', '__tq3'), ('__tq4',)))

    def test_compatibility_hack(self):
        assert Type('int', '*', ()).add_compatibility_hack() == \
               Type(Type('int', '*'), ())
        assert Type('int', '*', (), '*').add_compatibility_hack() == \
               Type('int', '*', (), '*')
        assert Type('int', (), type_quals=(('const',), ('__interrupt',)))\
                   .add_compatibility_hack() == \
               Type(Type('int', type_quals=(('const',),)), (),
                    type_quals=((), ('__interrupt',),))

        assert Type(Type('int', '*'), ()).remove_compatibility_hack() == \
               Type('int', '*', ())
        assert Type('int', '*', ()).remove_compatibility_hack() == \
               Type('int', '*', ())

    def test_repr(self):
        assert repr(Type('int', '*')) == "Type({!r}, {!r})".format('int', '*')
        assert repr(Type('int', '*', type_quals=(('volatile',), ()))) == \
               ('Type({!r}, {!r}, type_quals=(({!r},), ()))'
                .format('int', '*', 'volatile'))


class TestStructUnion(object):

    TEST_MEMBERS = [ ('a', Type('int'), None),
                     ('b', Type('char', '*'), None)]

    def test_init(self):
        assert Struct().members == []
        assert Struct().pack == None
        assert Struct(*self.TEST_MEMBERS).members == self.TEST_MEMBERS
        assert Struct(pack=2).pack == 2

        assert Union(*self.TEST_MEMBERS).members == self.TEST_MEMBERS

    def test_list_equality(self):
        assert Struct(*self.TEST_MEMBERS, pack=2) == {
            'members': [ ('a', Type('int'), None),
                         ('b', Type('char', '*'), None)],
            'pack': 2 }
        assert issubclass(Struct, dict)

        assert Union(*self.TEST_MEMBERS)['members'] == self.TEST_MEMBERS

    def test_repr(self):
        assert repr(Struct()) == 'Struct()'
        assert repr(Struct(*self.TEST_MEMBERS, pack=2)) == \
               ( 'Struct(' + repr(self.TEST_MEMBERS[0]) + ', ' +
                 repr(self.TEST_MEMBERS[1]) + ', pack=2)' )
        assert repr(Union()) == 'Union()'


class TestEnum(object):

    def test_dict_equality(self):
        assert Enum(a=1, b=2) == {'a':1, 'b':2}
        assert issubclass(Enum, dict)


    def test_repr(self):
        assert repr(Enum(a=1, b=2)) == 'Enum(a=1, b=2)'


class TestFileHandling(object):
    """Test parser basic file operations.

    """

    h_dir = os.path.join(H_DIRECTORY, 'file_handling')

    def setup(self):

        self.parser = CParser(process_all=False)

    def test_init(self):
        parser = CParser(os.path.join(self.h_dir, 'replace.h'))
        assert parser.files is not None

    def test_find_file(self):

        saved_headers = pyclibrary.utils.HEADER_DIRS
        try:
            pyclibrary.utils.add_header_locations([self.h_dir])
            assert self.h_dir in pyclibrary.utils.HEADER_DIRS
            assert self.parser.find_headers(['replace.h']) == \
                   [os.path.join(self.h_dir, 'replace.h')]
        finally:
            pyclibrary.utils.HEADER_DIRS = saved_headers

        abs_hdr_path = os.path.join(self.h_dir, 'replace.h')
        assert self.parser.find_headers([abs_hdr_path]) == [abs_hdr_path]
        abs_hdr_path2 = os.path.join(self.h_dir, 'c_comments.h')
        assert len(self.parser.find_headers([abs_hdr_path, abs_hdr_path2])) == 2


    def test_load_file(self):

        path = os.path.join(self.h_dir, 'replace.h')
        assert self.parser.load_file(path)
        assert self.parser.files[path] is not None
        assert self.parser.file_order == [path]
        assert self.parser.init_opts['replace']['replace.h'] is None
        assert self.parser.init_opts['files'] == ['replace.h']

    def test_load_file_and_replace(self):

        path = os.path.join(self.h_dir, 'replace.h')
        rep = {'{placeholder}': '1', 'placeholder2': '2'}
        assert self.parser.load_file(path, rep)

        lines = self.parser.files[path].split('\n')
        assert lines[3] == '# define MACRO 1'
        assert lines[6] == '    # define MACRO2 2'

        lines[3] = '# define MACRO {placeholder}'
        lines[6] = '    # define MACRO2 placeholder2'
        with open(path) as f:
            compare_lines(lines, f.readlines())

        assert self.parser.file_order == [path]
        assert self.parser.init_opts['replace']['replace.h'] == rep
        assert self.parser.init_opts['files'] == ['replace.h']

    def test_load_non_existing_file(self):

        path = os.path.join(self.h_dir, 'no.h')
        assert not self.parser.load_file(path)
        assert self.parser.files[path] is None

    def test_removing_c_comments(self):

        path = os.path.join(self.h_dir, 'c_comments.h')
        self.parser.load_file(path)
        self.parser.remove_comments(path)
        with open(os.path.join(self.h_dir, 'c_comments_removed.h'), 'rU') as f:
            compare_lines(self.parser.files[path].split('\n'), f.readlines())

    def test_removing_cpp_comments(self):

        path = os.path.join(self.h_dir, 'cpp_comments.h')
        self.parser.load_file(path)
        self.parser.remove_comments(path)
        with open(os.path.join(self.h_dir,
                               'cpp_comments_removed.h'), 'rU') as f:
            compare_lines(self.parser.files[path].split('\n'), f.readlines())


class TestPreprocessing(object):
    """Test preprocessing.

    """
    h_dir = os.path.join(H_DIRECTORY, 'macros')

    def setup(self):

        self.parser = CParser(process_all=False)

    def test_values(self):

        path = os.path.join(self.h_dir, 'macro_values.h')
        self.parser.load_file(path)
        self.parser.remove_comments(path)
        self.parser.preprocess(path)

        macros = self.parser.defs['macros']
        values = self.parser.defs['values']

        assert 'M' in macros and macros['M'] == ''
        assert 'N' in macros and macros['N'] == 'n' and values['N'] is None

        # Decimal integer
        assert ('MACRO_D1' in macros and macros['MACRO_D1'] == '1' and
                values['MACRO_D1'] == 1)
        assert ('MACRO_D2' in macros and macros['MACRO_D2'] == '-2U' and
                values['MACRO_D2'] == -2)
        assert ('MACRO_D3' in macros and macros['MACRO_D3'] == '+ 3UL' and
                values['MACRO_D3'] == 3)

        # Bit shifted decimal integer
        assert ('MACRO_SD1' in macros and
                macros['MACRO_SD1'] == '(1 << 1)' and
                values['MACRO_SD1'] == 2)
        assert ('MACRO_SD2' in macros and
                macros['MACRO_SD2'] == '(2U << 2)' and
                values['MACRO_SD2'] == 8)
        assert ('MACRO_SD3' in macros and
                macros['MACRO_SD3'] == '(3UL << 3)' and
                values['MACRO_SD3'] == 24)

        # Hexadecimal integer
        assert ('MACRO_H1' in macros and
                macros['MACRO_H1'] == '+0x000000' and
                values['MACRO_H1'] == 0)
        assert ('MACRO_H2' in macros and
                macros['MACRO_H2'] == '- 0x000001U' and
                values['MACRO_H2'] == -1)
        assert ('MACRO_H3' in macros and
                macros['MACRO_H3'] == '0X000002UL' and
                values['MACRO_H3'] == 2)

        # Bit shifted hexadecimal integer
        assert ('MACRO_SH1' in macros and
                macros['MACRO_SH1'] == '(0x000000 << 1)' and
                values['MACRO_SH1'] == 0)
        assert ('MACRO_SH2' in macros and
                macros['MACRO_SH2'] == '(0x000001U << 2)' and
                values['MACRO_SH2'] == 4)
        assert ('MACRO_H3' in macros and
                macros['MACRO_SH3'] == '(0X000002UL << 3)' and
                values['MACRO_SH3'] == 16)

        # Floating point value
        assert ('MACRO_F1' in macros and
                macros['MACRO_F1'] == '1.0' and
                values['MACRO_F1'] == 1.0)
        assert ('MACRO_F2' in macros and
                macros['MACRO_F2'] == '1.1e1' and
                values['MACRO_F2'] == 11.)
        assert ('MACRO_F3' in macros and
                macros['MACRO_F3'] == '-1.1E-1' and
                values['MACRO_F3'] == -0.11)

        # String macro
        assert ('MACRO_S' in macros and macros['MACRO_S'] == '"test"' and
                values['MACRO_S'] == 'test')

        # Nested macros
        assert ('NESTED' in macros and macros['NESTED'] == '1' and
                values['NESTED'] == 1)
        assert ('NESTED2' in macros and macros['NESTED2'] == '1' and
                values['NESTED2'] == 1)
        assert ('MACRO_N' in macros and macros['MACRO_N'] == '1 + 2' and
                values['MACRO_N'] == 3)

        # Muliline macro
        assert 'MACRO_ML' in macros and values['MACRO_ML'] == 2

    def test_conditionals(self):

        path = os.path.join(self.h_dir, 'macro_conditionals.h')
        self.parser.load_file(path)
        self.parser.remove_comments(path)
        self.parser.preprocess(path)
        self.parser.parse_defs(path)

        macros = self.parser.defs['macros']
        stream = self.parser.files[path]

        # Test if defined conditional
        assert 'DEFINE_IF' in macros
        assert '  int DECLARE_IF;\n' in stream
        assert 'NO_DEFINE_IF' not in macros
        assert '  int NO_DECLARE_IF;\n' not in stream

        # Test ifdef conditional
        assert 'DEFINE_IFDEF' in macros
        assert '  int DECLARE_IFDEF;\n' in stream
        assert 'NO_DEFINE_IFDEF' not in macros
        assert '  int NO_DECLARE_IFDEF;\n' not in stream

        # Test if !defined
        assert 'DEFINE_IFN' in macros
        assert '  int DECLARE_IFN;\n' in stream
        assert 'NO_DEFINE_IFN' not in macros
        assert '  int NO_DECLARE_IFN;\n' not in stream

        # Test ifndef
        assert 'DEFINE_IFNDEF' in macros
        assert '  int DECLARE_IFNDEF;\n' in stream
        assert 'NO_DEFINE_IFNDEF' not in macros
        assert '  int NO_DECLARE_IFNDEF;\n' not in stream

        # Test elif
        assert 'DEFINE_ELIF' in macros
        assert '  int DECLARE_ELIF;\n' in stream
        assert 'NO_DEFINE_ELIF' not in macros
        assert '  int NO_DECLARE_ELIF;\n' not in stream

        # Test else
        assert 'DEFINE_ELSE' in macros
        assert '  int DECLARE_ELSE;\n' in stream
        assert 'NO_DEFINE_ELSE' not in macros
        assert '  int NO_DECLARE_ELSE;\n' not in stream

        # Test nested
        assert 'DEFINE_N1' in macros
        assert '  int DECLARE_N1;\n' in stream
        assert 'NO_DEFINE_N2' not in macros
        assert 'DEFINE_N2' not in macros

        assert 'DEFINE_N3' in macros
        assert 'NO_DEFINE_N3' not in macros
        assert '  int NO_DECLARE_N3;\n' not in stream

        # Test logical
        assert 'DEFINE_LOG' in macros
        assert '  int DECLARE_LOG;\n' in stream
        assert 'NO_DEFINE_LOG' not in macros
        assert 'NO_DEFINE_LOG' not in macros

        # Test undef
        assert 'DEFINE_UNDEF' in macros
        assert 'UNDEF' not in macros

    def test_macro_function(self):

        path = os.path.join(self.h_dir, 'macro_functions.h')
        self.parser.load_file(path)
        self.parser.remove_comments(path)
        self.parser.preprocess(path)
        self.parser.parse_defs(path)

        values = self.parser.defs['values']
        fnmacros = self.parser.defs['fnmacros']
        stream = self.parser.files[path]

        # Test macro declaration.
        assert 'CARRE' in fnmacros
        assert 'int carre = 2*2;' in stream

        assert 'int __declspec(dllexport) function2()' in stream
        assert '__declspec(dllexport) int function3()' in stream

        # Test defining a macro function as an alias for another one.
        assert 'MAKEINTRESOURCEA' in fnmacros
        assert 'MAKEINTRESOURCEW' in fnmacros
        assert 'MAKEINTRESOURCE' in fnmacros
        assert fnmacros['MAKEINTRESOURCE'] == fnmacros['MAKEINTRESOURCEA']
        assert 'int x = ((LPSTR)((ULONG_PTR)((WORD)(4))))'

        # Test using a macro value in a macro function call
        assert 'BIT' in values and values['BIT'] == 1
        assert '((y) |= (0x01))' in stream

        # Test defining a macro function calling other macros (values and
        # functions)
        assert 'SETBITS' in fnmacros
        assert 'int z1, z2 = (((1) |= (0x01)), ((2) |= (0x01)));' in stream

        # Test defining a macro function calling nested macro functions
        assert 'SETBIT_AUTO' in fnmacros
        assert 'int z3 = ((((3) |= (0x01)), ((3) |= (0x01))));' in stream

    def test_pragmas(self):

        path = os.path.join(self.h_dir, 'pragmas.h')
        self.parser.load_file(path)
        self.parser.remove_comments(path)
        self.parser.preprocess(path)
        self.parser.parse_defs(path)

        stream = self.parser.files[path]
        packings = self.parser.pack_list[path]

        # Check all pragmas instructions have been removed.
        assert stream.strip() == ''

        assert packings[1][1] is None
        assert packings[2][1] == 4
        assert packings[3][1] == 16
        assert packings[4][1] is None
        assert packings[5][1] is None
        assert packings[6][1] == 4
        assert packings[7][1] == 16
        assert packings[8][1] is None


class TestParsing(object):
    """Test parsing.

    """

    h_dir = H_DIRECTORY

    def setup(self):

        self.parser = CParser(process_all=False)

    def test_variables(self):

        path = os.path.join(self.h_dir, 'variables.h')
        self.parser.load_file(path)
        self.parser.process_all()

        vars = self.parser.clib_intf.vars

        # Integers
        assert vars['short1'] == cm.BuiltinType('signed short')
        assert vars['short_int'] == cm.BuiltinType('short int')
        assert vars['short_un'] == cm.BuiltinType('unsigned short')
        assert vars['short_int_un'] == cm.BuiltinType('unsigned short int')
        assert vars['int1'] == cm.BuiltinType('int')
        assert vars['un'] == cm.BuiltinType('unsigned')
        assert vars['int_un'] == cm.BuiltinType('unsigned int')
        assert vars['long1'] == cm.BuiltinType('long')
        assert vars['long_int'] == cm.BuiltinType('long int')
        assert vars['long_un'] == cm.BuiltinType('unsigned long')
        assert vars['long_int_un'] == cm.BuiltinType('unsigned long int')
        if sys.platform == 'win32':   ###TODO: this has to be dependend on CParser objects, not on hosting opering system
            assert vars['int64'] == cm.BuiltinType('__int64')
            assert vars['int64_un'] == cm.BuiltinType('unsigned __int64')
        assert vars['long_long'] == cm.BuiltinType('long long')
        assert vars['long_long_int'] == cm.BuiltinType('long long int')
        assert vars['long_long_un'] == cm.BuiltinType('unsigned long long')
        assert (vars['long_long_int_un'] ==
                cm.BuiltinType('unsigned long long int'))

        # Floating point number
        assert vars['fl'] == cm.BuiltinType('float')
        assert vars['db'] == cm.BuiltinType('double')
        assert vars['dbl'] == cm.BuiltinType('long double')

        # Const and static modif
        assert vars['int_const'] == cm.BuiltinType('int', quals=['const'])
        assert vars['int_stat'] == cm.BuiltinType('int')
        assert vars['int_con_stat'] == cm.BuiltinType('int', quals=['const'])
        assert vars['int_extern'] == cm.BuiltinType('int')

        # String
        assert vars['str1'] == cm.PointerType(cm.BuiltinType('char'))
        assert (vars['str2'] ==
                cm.PointerType(cm.PointerType(cm.BuiltinType('char'))))
        assert (vars['str3'] ==
                cm.PointerType(cm.BuiltinType('char', quals=['const']),
                               quals=['const']))   ### test initial_val?
        assert 'str4' in vars     ### test initial_val?
        assert 'str5' in vars     ### test initial_val?

        # Test complex evaluation
        assert 'x1' in vars    ### test initial_val == 1.0?

        # Test type casting handling.
        assert 'x2' in vars    ### test initial_val == 88342528?

        # Test array handling
        assert vars['array'] == cm.ArrayType(cm.BuiltinType('float'), 2) ### test initial_val?
        assert (vars['intJunk'] ==
                cm.ArrayType(
                    cm.PointerType(
                        cm.PointerType(
                            cm.PointerType(
                                cm.BuiltinType('int', quals=['const']),
                                quals=['const']))),
                    4))
        assert vars['undef_size_array'] == cm.ArrayType(cm.BuiltinType('int'))

        # test type qualifiers
        assert (vars['typeQualedIntPtrPtr'] ==
                cm.PointerType(
                    cm.PointerType(
                        cm.BuiltinType('int', quals=['const']),
                        quals=['volatile'])))
        assert (vars['typeQualedIntPtr'] ==
                cm.PointerType(
                    cm.BuiltinType('int', quals=['const', 'volatile'])))

        # test type definition precedence
        assert (vars['prec_ptr_of_arr'] ==
                cm.PointerType(cm.ArrayType(cm.BuiltinType('int'), 1)))
        assert (vars['prec_arr_of_ptr'] ==
                cm.ArrayType(cm.PointerType(cm.BuiltinType('int')), 1))
        assert (vars['prec_arr_of_ptr2'] == \
                cm.ArrayType(cm.PointerType(cm.BuiltinType('int')), 1))

        # test filemap
        assert (os.path.basename(self.parser.clib_intf.file_map['short1']) ==
                'variables.h')

    # No structure, no unions, no enum
    def test_typedef(self):

        path = os.path.join(self.h_dir, 'typedefs.h')
        self.parser.load_file(path)
        self.parser.process_all()

        types = self.parser.defs['types']
        variables = self.parser.defs['variables']
        tdefs = self.parser.clib_intf.typedefs
        vars = self.parser.clib_intf.vars

        # Test defining types from base types.
        assert (tdefs['typeChar'] ==
                cm.PointerType(cm.PointerType(cm.BuiltinType('char'))))
        assert tdefs['typeInt'] == cm.BuiltinType('int')
        assert tdefs['typeIntPtr'] == cm.PointerType(cm.BuiltinType('int'))
        assert tdefs['typeIntArr'] == cm.ArrayType(cm.BuiltinType('int'), 10)
        assert (tdefs['typeIntDArr'] ==
                cm.ArrayType(cm.ArrayType(cm.BuiltinType('int'), 6), 5))
        assert tdefs['typeTypeInt'] == cm.CustomType('typeInt')
        assert tdefs['typeTypeInt'].resolve(tdefs) == cm.BuiltinType('int')
        assert tdefs['ULONG'] == cm.BuiltinType('unsigned long')

        # Test annotated types
        assert (tdefs['voidpc'] ==
                cm.PointerType(cm.BuiltinType('void', quals=['const'])))
        assert (tdefs['charf'] == cm.BuiltinType('char', quals=['far']))

        # Test using custom type.
        assert (vars['ttip5'] ==
                cm.ArrayType(
                    cm.PointerType(
                        cm.CustomType('typeTypeInt')),
                    5))

        # Handling undefined types
        assert tdefs['SomeOtherType'] == cm.CustomType('someType')
        assert vars['x'] == cm.CustomType('undefined')
        with raises(cm.UnknownCustomTypeError):
            vars['x'].resolve(tdefs)

        # Testing recursive defs
        assert 'recType1' in tdefs
        assert 'recType2' in tdefs
        assert 'recType3' in tdefs
        with raises(cm.UnknownCustomTypeError):
            tdefs['recType3'].resolve(tdefs)

        # test filemap
        assert (os.path.basename(self.parser.clib_intf.file_map['ULONG']) ==
                'typedefs.h')

    def test_enums(self):

        path = os.path.join(self.h_dir, 'enums.h')
        self.parser.load_file(path)
        self.parser.process_all()

        tdefs = self.parser.clib_intf.typedefs
        vars = self.parser.clib_intf.vars
        enums = self.parser.clib_intf.enums

        # test all properties of enum
        enum_name_type = cm.EnumType([('enum1', 2), ('enum2', 6),
                                      ('enum3', 7), ('enum4', 8)])
        assert tdefs['enum enum_name'] == enum_name_type
        assert vars['enum_inst'] == cm.CustomType('enum enum_name')

        # test anonymous enums
        assert vars['no_name_enum_inst'] == cm.CustomType('enum anon_enum0')
        assert vars['no_name_enum_inst2'] == cm.CustomType('enum anon_enum1')
        assert tdefs['enum anon_enum0'] == cm.EnumType([('x', 0), ('y', 1)])

        assert enums['y'] == 1

        # test filemap
        enum_name_path = self.parser.clib_intf.file_map['enum enum_name']
        assert os.path.basename(enum_name_path) == 'enums.h'

    def test_struct(self):

        path = os.path.join(self.h_dir, 'structs.h')
        self.parser.load_file(path)
        self.parser.process_all()

        tdefs = self.parser.clib_intf.typedefs
        vars = self.parser.clib_intf.vars

        # Test creating a structure using only base types.
        assert (tdefs['struct struct_name'] ==
                cm.StructType([('x', cm.BuiltinType('int'), None),
                               ('y', cm.CustomType('type_type_int'), None),
                               ('str', cm.ArrayType(cm.BuiltinType('char'),
                                                    10), None)]))
        assert vars['struct_inst'] == cm.CustomType('struct struct_name')

        # Test creating a pointer type from a structure.
        assert (tdefs['struct_name_ptr'] ==
                cm.PointerType(cm.CustomType('struct struct_name')))

        assert (tdefs['struct_name2_ptr'] ==
                cm.PointerType(cm.CustomType('struct anon_struct0')))

        # Test declaring a recursive structure.
        assert (tdefs['struct recursive_struct'] ==
                cm.StructType([('next', cm.PointerType(
                    cm.CustomType('struct recursive_struct')), None)]))

        # Test declaring near and far pointers.
        assert (tdefs['NPWNDCLASSEXA'] ==
                cm.PointerType(cm.CustomType('struct tagWNDCLASSEXA',
                                             quals=['near'])))

        # Test altering the packing of a structure.
        assert (tdefs['struct struct_name_p'] ==
               cm.StructType([('x', cm.BuiltinType('int'), None),
                              ('y', cm.CustomType('type_type_int'), None),
                              ('str', cm.ArrayType(cm.BuiltinType('char'),
                                                   10),
                               None)],
                             packsize=16))

        assert tdefs['struct default_packsize'].packsize is None

        assert (tdefs['struct unnamed_struct'] ==
                cm.StructType([
                    (None, cm.CustomType('struct struct_name'), None)]))

        assert tdefs['struct typequals'].quals == []
        assert vars['typequals_var'].quals == ['const', 'volatile']

        # test filemap
        strct_name_path = self.parser.clib_intf.file_map['struct struct_name']
        assert os.path.basename(strct_name_path) == 'structs.h'

    def test_unions(self):

        path = os.path.join(self.h_dir, 'unions.h')
        self.parser.load_file(path)
        self.parser.process_all()

        tdefs = self.parser.clib_intf.typedefs
        vars = self.parser.clib_intf.vars

        # Test declaring an union.
        assert (tdefs['union union_name'] ==
                cm.UnionType([('x', cm.BuiltinType('int')),
                              ('y', cm.BuiltinType('int'))]))
        assert (tdefs['union_name_ptr'] ==
                cm.PointerType(cm.CustomType('union union_name')))

        # Test defining an unnamed union
        assert (vars['no_name_union_inst'] ==
                cm.CustomType('union anon_union0'))


        # Test defining a structure using an unnamed union internally.
        assert (tdefs['struct tagRID_DEVICE_INFO'] ==
                cm.StructType([
                    ('cbSize', cm.CustomType('DWORD'), None),
                    ('dwType', cm.CustomType('DWORD'), None),
                    (None, cm.CustomType('union anon_union1'), None)]))

        assert (tdefs['RID_DEVICE_INFO'] ==
                cm.CustomType('struct tagRID_DEVICE_INFO'))
        assert (tdefs['PRID_DEVICE_INFO'] ==
                cm.PointerType(cm.CustomType('struct tagRID_DEVICE_INFO')))
        assert (tdefs['LPRID_DEVICE_INFO'] ==
                cm.PointerType(cm.CustomType('struct tagRID_DEVICE_INFO')))

        # test filemap
        union_name_path = self.parser.clib_intf.file_map['union union_name']
        assert os.path.basename(union_name_path) == 'unions.h'

    def test_functions(self):

        path = os.path.join(self.h_dir, 'functions.h')
        self.parser.load_file(path)
        self.parser.process_all()

        functions = self.parser.defs['functions']
        variables = self.parser.defs['variables']

        funcs = self.parser.clib_intf.funcs
        vars = self.parser.clib_intf.vars

        assert (funcs['f'] ==
                cm.FunctionType(
                    cm.BuiltinType('void'),
                    [(None, cm.BuiltinType('int')),
                     (None, cm.BuiltinType('int'))]))
        assert (funcs['g'] ==
                cm.FunctionType(
                    cm.BuiltinType('int'),
                    [('ch', cm.PointerType(cm.BuiltinType('char'))),
                     ('str', cm.PointerType(cm.PointerType(
                         cm.BuiltinType('char'))))])
                )
        assert (vars['fnPtr'] ==
                cm.PointerType(
                    cm.FunctionType(
                        cm.BuiltinType('int'),
                        [(None, cm.BuiltinType('char')),
                         (None, cm.BuiltinType('float'))])))
        assert (funcs['function1'] ==
                cm.FunctionType(
                    cm.BuiltinType('int'),
                    [],
                    quals=['__stdcall']))
        assert (funcs['function2'] ==
                cm.FunctionType(cm.BuiltinType('int'), []))

        assert 'externFunc' in funcs

        ptyp = cm.PointerType(
            cm.PointerType(
                cm.BuiltinType('int', quals=['volatile']),
                quals=['const']))
        assert (funcs['typeQualedFunc'] ==
                cm.FunctionType(cm.BuiltinType('int'), [(None, ptyp)]))

        # test filemap
        f_name_path = self.parser.clib_intf.file_map['f']
        assert os.path.basename(f_name_path) == 'functions.h'
        g_name_path = self.parser.clib_intf.file_map['g']
        assert os.path.basename(g_name_path) == 'functions.h'

        ###TODO: add __declspec() qualifier support
