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
from pyclibrary.c_parser import CParser
import pyclibrary.utils


H_DIRECTORY = os.path.join(os.path.dirname(__file__), 'headers')


def compare_lines(lines, lines2):
    """Compare lines striped from whitespaces characters.

    """
    for l, l_test in zip(lines, lines2):
        assert l.strip() == l_test.strip()


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

        variables = self.parser.defs['variables']

        # Integers
        assert ('short1' in variables and
                variables['short1'] == (1, ('signed short',)))
        assert ('short_int' in variables and
                variables['short_int'] == (1, ('short int',)))
        assert ('short_un' in variables and
                variables['short_un'] == (1, ('unsigned short',)))
        assert ('short_int_un' in variables and
                variables['short_int_un'] == (1, ('unsigned short int',)))
        assert ('int1' in variables and
                variables['int1'] == (1, ('int',)))
        assert ('un' in variables and
                variables['un'] == (1, ('unsigned',)))
        assert ('int_un' in variables and
                variables['int_un'] == (1, ('unsigned int',)))
        assert ('long1' in variables and
                variables['long1'] == (1, ('long',)))
        assert ('long_int' in variables and
                variables['long_int'] == (1, ('long int',)))
        assert ('long_un' in variables and
                variables['long_un'] == (1, ('unsigned long',)))
        assert ('long_int_un' in variables and
                variables['long_int_un'] == (1, ('unsigned long int',)))
        if sys.platform == 'win32':
            assert ('int64' in variables and
                    variables['int64'] == (1, ('__int64',)))
            assert ('int64_un' in variables and
                    variables['int64_un'] == (1, ('unsigned __int64',)))
        assert ('long_long' in variables and
                variables['long_long'] == (1, ('long long',)))
        assert ('long_long_int' in variables and
                variables['long_long_int'] == (1, ('long long int',)))
        assert ('long_long_un' in variables and
                variables['long_long_un'] == (1, ('unsigned long long',)))
        assert ('long_long_int_un' in variables and
                variables['long_long_int_un'] == (1,
                                                  ('unsigned long long int',)))

        # Floating point number
        assert ('fl' in variables and variables['fl'] == (1., ('float',)))
        assert ('db' in variables and variables['db'] == (0.1, ('double',)))
        assert ('dbl' in variables and
                variables['dbl'] == (-10., ('long double',)))

        # Const and static modif
        assert ('int_const' in variables and
                variables['int_const'] == (4, ('int',)))
        assert ('int_stat' in variables and
                variables['int_stat'] == (4, ('int',)))
        assert ('int_con_stat' in variables and
                variables['int_con_stat'] == (4, ('int',)))
        assert ('int_extern' in variables and
                variables['int_extern'] == (4, ('int',)))

        # String
        assert ('str1' in variables and
                variables['str1'] == ("normal string", ('char', '*')))
        assert ('str2' in variables and
                variables['str2'] == ("string with macro: INT",
                                      ('char', '*', '*')))
        assert ('str3' in variables and
                variables['str3'] == ("string with comment: /*comment inside string*/",
                                      ('char', '*')))
        assert ('str4' in variables and
                variables['str4'] == ("string with define #define MACRO5 macro5_in_string ",
                                      ('char', '*')))
        assert ('str5' in variables and
                variables['str5'] == ("string with \"escaped quotes\" ",
                                      ('char', '*')))

        # Test complex evaluation
        assert ('x1' in variables and
                variables['x1'] == (1., ('float',)))

        # Test type casting handling.
        assert ('x2' in variables and
                variables['x2'] == (88342528, ('int',)))

        # Test array handling
        assert ('array' in variables and
                variables['array'] == ([1, 3141500.0], ('float', [2])))
        assert ('intJunk' in variables and
                variables['intJunk'] == (None, (u'int', u'*', u'*', u'*', [4])))

    # No structure, no unions, no enum
    def test_typedef(self):

        path = os.path.join(self.h_dir, 'typedefs.h')
        self.parser.load_file(path)
        self.parser.process_all()

        types = self.parser.defs['types']
        variables = self.parser.defs['variables']

        # Test defining types from base types.
        assert ('typeChar' in types and types['typeChar'] == ('char', '*', '*'))
        assert ('typeInt' in types and types['typeInt'] == ('int',))
        assert ('typeIntPtr' in types and types['typeIntPtr'] == ('int', '*'))
        assert ('typeIntArr' in types and types['typeIntArr'] == ('int', [10]))
        assert ('typeTypeInt' in types and
                types['typeTypeInt'] == ('typeInt',))
        assert not self.parser.is_fund_type('typeTypeInt')
        assert self.parser.eval_type(['typeTypeInt']) == ('int',)
        assert ('ULONG' in types and types['ULONG'] == ('unsigned long',))

        # Test annotated types
        assert ('voidpc' in types and types['voidpc'] == ('void', '*'))
        assert ('charf' in types and types['charf'] == ('char',))

        # Test using custom type.
        assert ('ttip5' in variables and
                variables['ttip5'] == (None, ('typeTypeInt', '*', [5])))

        # Handling undefined types
        assert ('SomeOtherType' in types and
                types['SomeOtherType'] == ('someType',))
        assert ('x' in variables and variables['x'] == (None, ('undefined',)))
        assert not self.parser.is_fund_type('SomeOtherType')
        with raises(Exception):
            self.parser.eval_type(('undefined',))

        # Testing recursive defs
        assert 'recType1' in types
        assert 'recType2' in types
        assert 'recType3' in types
        with raises(Exception):
            self.parser.eval_type(('recType3',))

    def test_enums(self):

        path = os.path.join(self.h_dir, 'enums.h')
        self.parser.load_file(path)
        self.parser.process_all()

        enums = self.parser.defs['enums']
        types = self.parser.defs['types']
        variables = self.parser.defs['variables']
        assert ('enum_name' in enums and 'enum enum_name' in types)
        assert enums['enum_name'] == {'enum1': 2, 'enum2': 6, 'enum3': 7,
                                      'enum4': 8}
        assert types['enum enum_name'] == ('enum', 'enum_name',)
        assert ('enum_inst' in variables and
                variables['enum_inst'] == (None, ('enum enum_name',)))

        assert 'anon_enum0' in enums

    def test_struct(self):

        path = os.path.join(self.h_dir, 'structs.h')
        self.parser.load_file(path)
        self.parser.process_all()

        structs = self.parser.defs['structs']
        types = self.parser.defs['types']
        variables = self.parser.defs['variables']

        # Test creating a structure using only base types.
        assert ('struct_name' in structs and 'struct struct_name' in types)
        assert {'members': [('x', ('int',), 1),
                            ('y', ('type_type_int',), None, 2),
                            ('str', ('char', [10]), None)],
                'pack': None} == structs['struct_name']
        assert ('struct_inst' in variables and
                variables['struct_inst'] == (None, ('struct struct_name',)))

        # Test creating a pointer type from a structure.
        assert ('struct_name_ptr' in types and
                types['struct_name_ptr'] == ('struct struct_name', '*'))

        assert ('struct_name2_ptr' in types and
                types['struct_name2_ptr'] == ('struct anon_struct0',
                                              '*'))

        # Test declaring a recursive structure.
        assert ('recursive_struct' in structs and
                'struct recursive_struct' in types)
        assert {'members': [('next', ('struct recursive_struct', '*'), None)],
                'pack': None} == structs['recursive_struct']

        # Test declaring near and far pointers.
        assert 'tagWNDCLASSEXA' in structs
        assert ('NPWNDCLASSEXA' in types and
                types['NPWNDCLASSEXA'] == ('struct tagWNDCLASSEXA', '*'))

        # Test altering the packing of a structure.
        assert ('struct_name_p' in structs and 'struct struct_name_p' in types)
        assert {'members': [('x', ('int',), None),
                            ('y', ('type_type_int',), None),
                            ('str', ('char', [10]), "brace }  \0")],
                'pack': 16} == structs['struct_name_p']

    def test_unions(self):

        path = os.path.join(self.h_dir, 'unions.h')
        self.parser.load_file(path)
        self.parser.process_all()

        unions = self.parser.defs['unions']
        structs = self.parser.defs['structs']
        types = self.parser.defs['types']
        variables = self.parser.defs['variables']

        # Test declaring an union.
        assert 'union_name' in unions and 'union union_name' in types
        assert {'members': [('x', ('int',), 1),
                            ('y', ('int',), None)],
                'pack': None} == unions['union_name']
        assert ('union_name_ptr' in types and
                types['union_name_ptr'] == ('union union_name', '*'))

        # Test defining an unnamed union
        assert ('no_name_union_inst' in variables and
                variables['no_name_union_inst'] == (None,
                                                    ('union anon_union0',)))

        # Test defining a structure using an unnamed union internally.
        assert ('tagRID_DEVICE_INFO' in structs and
                {'members': [('cbSize', ('DWORD',), None),
                             ('dwType', ('DWORD',), None),
                             (None, ('union anon_union1',), None)],
                 'pack': None} == structs['tagRID_DEVICE_INFO'])

        assert ('RID_DEVICE_INFO' in types and
                types['RID_DEVICE_INFO'] == ('struct tagRID_DEVICE_INFO',))
        assert ('PRID_DEVICE_INFO' in types and
                types['PRID_DEVICE_INFO'] == ('struct tagRID_DEVICE_INFO', '*')
                )
        assert ('LPRID_DEVICE_INFO' in types and
                types['LPRID_DEVICE_INFO'] == ('struct tagRID_DEVICE_INFO',
                                               '*')
                )

    def test_functions(self):

        path = os.path.join(self.h_dir, 'functions.h')
        self.parser.load_file(path)
        self.parser.process_all()

        functions = self.parser.defs['functions']
        variables = self.parser.defs['variables']

        assert ('f' in functions and
                functions['f'] == (('void',),
                                   ((None, ('int',), None),
                                    (None, ('int',), None))))
        assert ('g' in functions and
                functions['g'] == (('int',),
                                   (('ch', ('char', '*'), None),
                                    ('str', ('char', '*', '*'), None))))
        assert ('fnPtr' in variables and
                variables['fnPtr'] == (None, ('int',
                                              ((None, ('char',), None),
                                               (None, ('float',), None)),
                                              '*')))
        assert ('function1' in functions and
                functions['function1'] == (('int', '__stdcall'), ()))

        assert ('function2' in functions and
                functions['function2'] == (('int',), ()))
