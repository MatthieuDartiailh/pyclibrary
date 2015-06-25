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
import tempfile
import shutil
from pytest import raises
from pyclibrary.c_parser import CParser, InvalidCacheError
import pyclibrary.utils
from pyclibrary import errors as err
import pyclibrary.c_model as cm


H_DIRECTORY = 'headers'


def compare_lines(lines, lines2):
    """Compare lines striped from whitespaces characters.

    """
    for l, l_test in zip(lines, lines2):
        assert l.strip() == l_test.strip()


class TestFileHandling(object):
    """Test parser basic file operations.

    """

    def hdr_file_path(self, name):
        this_dir = os.path.dirname(__file__)
        return os.path.join(this_dir, H_DIRECTORY, 'file_handling', name)

    def setup(self):
        self.parser = CParser()

    def test_find_file(self):
        ###TODO: assign find-headers to cparser (not global!)
        saved_headers = pyclibrary.utils.HEADER_DIRS
        try:
            this_dir = os.path.dirname(__file__)
            h_dir = os.path.join(this_dir, H_DIRECTORY, 'file_handling')
            pyclibrary.utils.add_header_locations([h_dir])
            assert h_dir in pyclibrary.utils.HEADER_DIRS
            assert self.parser.find_headers(['replace.h']) == \
                   [os.path.join(h_dir, 'replace.h')]
        finally:
            pyclibrary.utils.HEADER_DIRS = saved_headers

        abs_hdr_path = os.path.join(h_dir, 'replace.h')
        assert self.parser.find_headers([abs_hdr_path]) == [abs_hdr_path]
        abs_hdr_path2 = os.path.join(h_dir, 'c_comments.h')
        assert len(self.parser.find_headers(
                   [abs_hdr_path, abs_hdr_path2])) == 2


    def test_load_file(self):
        path = self.hdr_file_path('replace.h')
        self.parser.parse(path, load_only=True)
        assert self.parser.files[path] is not None
        assert self.parser.file_order == [path]

    def test_load_file_and_replace(self):
        path = self.hdr_file_path('replace.h')
        rep = {'{placeholder}': '1', 'placeholder2': '2'}
        self.parser.parse(path, rep, load_only=True)

        lines = self.parser.files[path].split('\n')
        assert lines[3] == '# define MACRO 1'
        assert lines[6] == '    # define MACRO2 2'

        lines[3] = '# define MACRO {placeholder}'
        lines[6] = '    # define MACRO2 placeholder2'
        with open(path) as f:
            compare_lines(lines, f.readlines())

        assert self.parser.file_order == [path]

    def test_load_non_existing_file(self):
        path = self.hdr_file_path('no.h')
        with raises(OSError):
            self.parser.parse(path, load_only=True)
        assert path not in self.parser.files

    def test_removing_c_comments(self):
        path = self.hdr_file_path('c_comments.h')
        self.parser.parse(path, uncomment_only=True)
        with open(self.hdr_file_path('c_comments_removed.h'), 'rU') as f:
            compare_lines(self.parser.files[path].split('\n'), f.readlines())

    def test_removing_cpp_comments(self):
        path = self.hdr_file_path('cpp_comments.h')
        self.parser.parse(path, uncomment_only=True)
        with open(self.hdr_file_path('cpp_comments_removed.h'), 'rU') as f:
            compare_lines(self.parser.files[path].split('\n'), f.readlines())

    def test_process_multiple_files(self):
        clib_intf = cm.CLibInterface()
        parser = CParser(clib_intf)
        parser.parse(self.hdr_file_path('multi_file1.h'))
        parser.parse(self.hdr_file_path('multi_file2.h'))
        assert clib_intf['MACRO_A'].content == 'replaced_val_a'
        assert clib_intf['MACRO_B'].content == 'base_val_b'

        new_clib_intf = cm.CLibInterface()
        parser.swap_clib_intf(new_clib_intf)
        parser.parse(self.hdr_file_path('multi_file3.h'))
        assert parser.clib_intf['MACRO_A'].content == 'other_val_a'
        assert 'MACRO_B' not in parser.clib_intf
        assert clib_intf['MACRO_A'].content == 'replaced_val_a'

    def test_caching(self):
        temp_dir = tempfile.mkdtemp()
        try:
            cache_file_name = os.path.join(temp_dir, 'temp.cache')
            multi_file1_name = os.path.join(temp_dir, 'multi_file1.h')
            shutil.copy(self.hdr_file_path('multi_file1.h'), multi_file1_name)

            # create cache of clib_intf of multi_file2 & temporary multi_file1
            self.parser.parse(multi_file1_name)
            self.parser.parse(self.hdr_file_path('multi_file2.h'))
            self.parser.write_cache(cache_file_name)

            # test caching ok
            parser2 = CParser()
            parser2.load_cache(cache_file_name)
            assert parser2.clib_intf['MACRO_B'].content == 'base_val_b'

            # test header file modification detection
            open(multi_file1_name, "wt").write('\n//modification')
            with raises(InvalidCacheError):
                parser2.load_cache(cache_file_name, check_validity=True)

            # test ignoring outdated file
            parser3 = CParser()
            parser3.load_cache(cache_file_name)
            assert parser3.clib_intf['MACRO_B'].content == 'base_val_b'
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        parser = CParser()
        with raises(InvalidCacheError):
            parser.load_cache('invalid_file_name')


class TestPreprocessing(object):
    """Test preprocessing.

    """

    def hdr_file_path(self, name):
        this_dir = os.path.dirname(__file__)
        return os.path.join(this_dir, H_DIRECTORY, 'macros', name)

    def setup(self):
        self.parser = CParser()

    def test_invalid_define(self):
        with raises(err.DefinitionError):
            self.parser.parse(self.hdr_file_path('macro_invalid.h'))

    def test_values(self):
        self.parser.parse(self.hdr_file_path('macro_values.h'))

        macros = self.parser.clib_intf.macros
        values = self.parser.clib_intf.macro_vals

        assert macros['M'].content == ''
        assert macros['N'].content == 'n' and values['N'] is None

        # Decimal integer
        assert (macros['MACRO_D1'].content  == '1' and
                values['MACRO_D1'] == 1)
        assert (macros['MACRO_D2'].content == '-2U' and
                values['MACRO_D2'] == -2)
        assert (macros['MACRO_D3'].content == '+ 3UL' and
                values['MACRO_D3'] == 3)

        # Bit shifted decimal integer
        assert (macros['MACRO_SD1'].content == '(1 << 1)' and
                values['MACRO_SD1'] == 2)
        assert (macros['MACRO_SD2'].content == '(2U << 2)' and
                values['MACRO_SD2'] == 8)
        assert (macros['MACRO_SD3'].content == '(3UL << 3)' and
                values['MACRO_SD3'] == 24)

        # Hexadecimal integer
        assert (macros['MACRO_H1'].content == '+0x000000' and
                values['MACRO_H1'] == 0)
        assert (macros['MACRO_H2'].content == '- 0x000001U' and
                values['MACRO_H2'] == -1)
        assert (macros['MACRO_H3'].content == '0X000002UL' and
                values['MACRO_H3'] == 2)

        # Bit shifted hexadecimal integer
        assert (macros['MACRO_SH1'].content == '(0x000000 << 1)' and
                values['MACRO_SH1'] == 0)
        assert (macros['MACRO_SH2'].content == '(0x000001U << 2)' and
                values['MACRO_SH2'] == 4)
        assert (macros['MACRO_SH3'].content == '(0X000002UL << 3)' and
                values['MACRO_SH3'] == 16)

        # Floating point value
        assert (macros['MACRO_F1'].content == '1.0' and
                values['MACRO_F1'] == 1.0)
        assert (macros['MACRO_F2'].content == '1.1e1' and
                values['MACRO_F2'] == 11.)
        assert (macros['MACRO_F3'].content == '-1.1E-1' and
                values['MACRO_F3'] == -0.11)

        # String macro
        assert (macros['MACRO_S'].content == '"test"' and
                values['MACRO_S'] == 'test')

        # Nested macros
        assert (macros['NESTED'].content == '1' and
                values['NESTED'] == 1)
        assert (macros['NESTED2'].content == '1' and
                values['NESTED2'] == 1)
        assert (macros['MACRO_N'].content == '1 + 2' and
                values['MACRO_N'] == 3)

        # Muliline macro
        assert 'MACRO_ML' in macros and values['MACRO_ML'] == 2
        assert '$MACRO$' in macros

    def test_conditionals(self):
        path = self.hdr_file_path('macro_conditionals.h')
        self.parser.parse(path)

        macros = self.parser.clib_intf.macros
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
        path = self.hdr_file_path('macro_functions.h')
        self.parser.parse(path)

        values = self.parser.clib_intf.macro_vals
        macros = self.parser.clib_intf.macros
        stream = self.parser.files[path]

        # Test macro declaration.
        assert macros['CARRE'] == cm.FnMacro('a*a', ['a'])
        assert 'int carre = 2*2;' in stream

        assert 'int __declspec(dllexport) function2()' in stream
        assert '__declspec(dllexport) int function3()' in stream

        # Test defining a macro function as an alias for another one.
        assert (macros['MAKEINTRESOURCEA'] ==
                cm.FnMacro('((LPSTR)((ULONG_PTR)((WORD)(i))))', ['i']))
        assert (macros['MAKEINTRESOURCEW'] ==
                cm.FnMacro('((LPWSTR)((ULONG_PTR)((WORD)(i))))', ['i']))
        assert macros['MAKEINTRESOURCE'] is macros['MAKEINTRESOURCEA']
        assert 'int x = ((LPSTR)((ULONG_PTR)((WORD)(4))))' in stream

        # Test using a macro value in a macro function call
        assert 'BIT' in values and values['BIT'] == 1
        assert '((y) |= (0x01))' in stream

        # Test defining a macro function calling other macros (values and
        # functions)
        assert 'SETBITS' in macros
        assert 'int z1, z2 = (((1) |= (0x01)), ((2) |= (0x01)));' in stream

        # Test defining a macro function calling nested macro functions
        assert 'SETBIT_AUTO' in macros
        assert 'int z3 = ((((3) |= (0x01)), ((3) |= (0x01))));' in stream

    def test_pragmas(self):
        path = self.hdr_file_path('pragmas.h')
        self.parser.parse(path)

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

    def hdr_file_path(self, name):
        this_dir = os.path.dirname(__file__)
        return os.path.join(this_dir, H_DIRECTORY, name)

    def setup(self):
        self.clib_intf = cm.CLibInterface()
        self.parser = CParser(self.clib_intf)

    def test_variables(self):
        self.parser.parse(self.hdr_file_path('variables.h'))
        vars = self.clib_intf.vars

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
        assert (self.parser.clib_intf.storage_classes['int_extern'] ==
                ['extern'])

        # String
        assert vars['str1'] == cm.PointerType(cm.BuiltinType('char'))
        assert (vars['str2'] ==
                cm.PointerType(cm.PointerType(cm.BuiltinType('char'))))
        assert (vars['str3'] ==
                cm.PointerType(cm.BuiltinType('char', quals=['const']),
                               quals=['const']))
        assert 'str4' in vars
        assert 'str5' in vars

        # Test complex evaluation
        assert 'x1' in vars

        # Test type casting handling.
        assert 'x2' in vars

        # Test array handling
        assert vars['array'] == cm.ArrayType(cm.BuiltinType('float'), 2)
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
        assert (vars['prec_arr_of_ptr2'] ==
                cm.ArrayType(cm.PointerType(cm.BuiltinType('int')), 1))

        # test filemap
        assert (os.path.basename(self.parser.clib_intf.file_map['short1']) ==
                'variables.h')

        assert '$ms_type_qual_test' in vars

    # No structure, no unions, no enum
    def test_typedef(self):
        self.parser.parse(self.hdr_file_path('typedefs.h'))

        tdefs = self.clib_intf.typedefs
        vars = self.clib_intf.vars

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
        assert (tdefs['charv'] ==
                cm.BuiltinType('char', quals=['volatile']))

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
        self.parser.parse(self.hdr_file_path('enums.h'))

        tdefs = self.clib_intf.typedefs
        vars = self.clib_intf.vars
        enums = self.clib_intf.enums

        # test all properties of enum
        enum_name_type = cm.EnumType([('enum1', 9), ('enum2', 6),
                                      ('enum3', 7), ('enum4', 8)])
        assert tdefs['enum enum_name'] == enum_name_type
        assert vars['enum_inst'] == cm.CustomType('enum enum_name')
        assert vars['enum_inst2'] == cm.CustomType('enum enum_name')

        # test anonymous enums
        assert (vars['anonymous_enum_inst'] ==
                cm.PointerType(cm.EnumType([('x', 0), ('y', 1)])))
        assert set(tdefs) == { 'enum enum_name' }

        assert enums['enum1'] == 9
        assert enums['y'] == 1

        # test filemap
        enum_name_path = self.parser.clib_intf.file_map['enum enum_name']
        assert os.path.basename(enum_name_path) == 'enums.h'

    def test_struct(self):
        self.parser.parse(self.hdr_file_path('structs.h'))

        tdefs = self.clib_intf.typedefs
        vars = self.clib_intf.vars

        # Test creating a structure using only base types.
        assert (tdefs['struct struct_name'] ==
                cm.StructType([('x', cm.BuiltinType('int'), None),
                               ('y', cm.CustomType('type_type_int'), 2),
                               ('str', cm.ArrayType(cm.BuiltinType('char'),
                                                    10), None)]))
        assert vars['struct_inst'] == cm.CustomType('struct struct_name')

        # Test creating a pointer type from a structure.
        assert (tdefs['struct_name_ptr'] ==
                cm.PointerType(cm.CustomType('struct struct_name')))

        assert (tdefs['struct_name2_ptr'] ==
                cm.PointerType(cm.StructType([
                    ('x', cm.BuiltinType('int'), None),
                    ('y', cm.BuiltinType('int'), None),
                ])))

        # Test declaring a recursive structure.
        assert (tdefs['struct recursive_struct'] ==
                cm.StructType([('next', cm.PointerType(
                    cm.CustomType('struct recursive_struct')), None)]))

        # Test declaring near and far pointers.
        assert (tdefs['NPWNDCLASSEXA'] ==
                cm.PointerType(cm.CustomType('struct tagWNDCLASSEXA',
                                             quals=['__allowed("N")'])))

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

        sub_struct = cm.StructType([('y', cm.BuiltinType('int'), None)])
        assert (vars['anonymous_struct_inst'] ==
                cm.StructType([
                    ('x', cm.BuiltinType('long'), None),
                    (None, sub_struct, None)]))

        assert tdefs['struct typequals'].quals == []
        assert vars['typequals_var'].quals == ['const', 'volatile']

        # test filemap
        strct_name_path = self.parser.clib_intf.file_map['struct struct_name']
        assert os.path.basename(strct_name_path) == 'structs.h'

    def test_unions(self):
        self.parser.parse(self.hdr_file_path('unions.h'))

        tdefs = self.clib_intf.typedefs
        vars = self.clib_intf.vars

        # Test declaring an union.
        assert (tdefs['union union_name'] ==
                cm.UnionType([('x', cm.BuiltinType('int')),
                              ('y', cm.BuiltinType('int'))]))
        assert (tdefs['union_name_ptr'] ==
                cm.PointerType(cm.CustomType('union union_name')))

        # Test defining an unnamed union
        assert (vars['no_name_union_inst'] ==
                cm.UnionType([('x', cm.BuiltinType('int')),
                              ('y', cm.BuiltinType('int'))]))

        # Test defining a structure using an unnamed union internally.
        sub_union = cm.UnionType([
            ('mouse', cm.CustomType('RID_DEVICE_INFO_MOUSE')),
            ('keyboard', cm.CustomType('RID_DEVICE_INFO_KEYBOARD')),
            ('hid', cm.CustomType('RID_DEVICE_INFO_HID'))])
        assert (tdefs['struct tagRID_DEVICE_INFO'] ==
                cm.StructType([
                    ('cbSize', cm.CustomType('DWORD'), None),
                    ('dwType', cm.CustomType('DWORD'), None),
                    (None, sub_union, None)]))

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
        self.parser.parse(self.hdr_file_path('functions.h'))

        funcs = self.clib_intf.funcs
        vars = self.clib_intf.vars
        storage_classes = self.clib_intf.storage_classes

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
                         cm.BuiltinType('char'))))]))
        assert storage_classes['g'] == ['inline']
        assert (vars['fnPtr'] ==
                cm.PointerType(
                    cm.FunctionType(
                        cm.BuiltinType('int'),
                        [(None, cm.BuiltinType('char')),
                         (None, cm.BuiltinType('float'))])))
        assert (funcs['function1'] ==
                cm.FunctionType(cm.BuiltinType('int'), [], ['__stdcall']))
        assert (storage_classes['function1'] ==
                ['extern', '__declspec(dllexport)'])
        assert (storage_classes['pre_declspec_func'] ==
                ['__declspec(noreturn)'])
        assert (funcs['function2'] ==
                cm.FunctionType(cm.BuiltinType('int'), []))

        assert 'externFunc' in funcs
        assert storage_classes['externFunc'] == ['extern']

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

        assert (funcs['array_param_func'] ==
                cm.FunctionType(cm.BuiltinType('void'), [
                    ('arr_params', cm.ArrayType(
                        cm.BuiltinType('int'), None))]))
