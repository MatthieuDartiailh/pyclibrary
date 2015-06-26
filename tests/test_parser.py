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
import tempfile
import shutil
import io
from pytest import raises
from pyclibrary.c_parser import CParser, InvalidCacheError, MSVCParser
from pyclibrary import errors as err, DefinitionError
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
        this_dir = os.path.dirname(__file__)
        h_dir = os.path.join(this_dir, H_DIRECTORY, 'file_handling')
        abs_hdr_path = self.hdr_file_path('test.h')

        parser_withdir = CParser(header_dirs=[h_dir])
        assert (parser_withdir.find_header('test.h') ==
                os.path.join(h_dir, 'test.h'))
        assert parser_withdir.find_header(abs_hdr_path) == abs_hdr_path

        with raises(IOError):
            self.parser.find_header('test.h')
        assert self.parser.find_header(abs_hdr_path) == abs_hdr_path

    def test_fix_bad_code(self):
        rep = {'{placeholder}': '1', 'placeholder2': '2'}
        srccode = ('# define MACRO {placeholder}\n'
                   '\n'
                   '# ifdef MACRO\n'
                   '    # define MACRO2 placeholder2\n'
                   '# endif\n')
        lines = self.parser.fix_bad_code(srccode, rep).split('\n')

        assert lines[0] == '# define MACRO 1'
        assert lines[3] == '    # define MACRO2 2'

        lines[0] = '# define MACRO {placeholder}'
        lines[3] = '    # define MACRO2 placeholder2'
        compare_lines(lines, srccode.split('\n'))

    def test_load_non_existing_file(self):
        path = self.hdr_file_path('no.h')
        with raises(IOError):
            self.parser.read(path)
        assert path not in self.parser.file_order

    def test_removing_c_comments(self):
        srccode = open(self.hdr_file_path('c_comments.h')).read()
        nocomment_srccode = self.parser.remove_comments(srccode)

        with open(self.hdr_file_path('c_comments_removed.h'), 'rU') as f:
            compare_lines(nocomment_srccode.split('\n'), f.readlines())

    def test_removing_cpp_comments(self):
        srccode = open(self.hdr_file_path('cpp_comments.h')).read()
        nocomment_srccode = self.parser.remove_comments(srccode)
        with open(self.hdr_file_path('cpp_comments_removed.h'), 'rU') as f:
            compare_lines(nocomment_srccode.split('\n'), f.readlines())

    def test_process_multiple_files(self):
        parser = CParser()
        clib_intf = parser.clib_intf
        parser.read(self.hdr_file_path('multi_file1.h'))
        parser.read(self.hdr_file_path('multi_file2.h'))
        assert parser.file_order == [self.hdr_file_path('multi_file1.h'),
                                     self.hdr_file_path('multi_file2.h')]
        assert clib_intf['MACRO_A'].content == 'replaced_val_a'
        assert clib_intf['MACRO_B'].content == 'base_val_b'

        parser.reset_clib_intf()
        assert parser.file_order == []
        parser.read(self.hdr_file_path('multi_file3.h'))
        assert parser.clib_intf['MACRO_A'].content == 'other_val_a'
        assert 'MACRO_B' not in parser.clib_intf
        assert clib_intf['MACRO_A'].content == 'replaced_val_a'

    def test_caching(self):
        temp_dir = tempfile.mkdtemp()
        try:
            cache_file_name = os.path.join(temp_dir, 'temp.cache')
            test_filename = os.path.join(temp_dir, 'test.h')
            shutil.copy(self.hdr_file_path('test.h'), test_filename)

            # create cache of clib_intf of multi_file2 & temporary multi_file1
            self.parser.read(test_filename)
            self.parser.read(self.hdr_file_path('test2.h'))
            self.parser.write_cache(cache_file_name)

            # test caching ok
            parser2 = CParser()
            parser2.load_cache(cache_file_name)
            assert parser2.clib_intf['TEST'].content == '1'
            assert (parser2.file_order ==
                    [test_filename, self.hdr_file_path('test2.h')])

            # test wrong predefs
            predef_parser = CParser(predef_macros={'A': ''})
            with raises(InvalidCacheError):
                predef_parser.load_cache(cache_file_name, check_validity=True)

            # test header file modification detection
            open(test_filename, "wt").write('\n//modification')
            with raises(InvalidCacheError):
                parser2.load_cache(cache_file_name, check_validity=True)

            # test ignoring outdated file
            parser3 = CParser()
            parser3.load_cache(cache_file_name)
            assert parser3.clib_intf['TEST'].content == '1'
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        parser = CParser()
        with raises(InvalidCacheError):
            parser.load_cache('invalid_file_name')

    def test_read_fileobj(self):
        self.parser.read(io.StringIO('#define TEST is_defined'))
        assert 'TEST' in self.parser.clib_intf

    def test_filemap(self):
        test_filename = self.hdr_file_path('test.h')

        parser = CParser()
        parser.read(test_filename)
        assert parser.clib_intf.file_map['TEST'] == test_filename

        parser = CParser()
        parser.read(test_filename, virtual_filename='/file/name')
        assert parser.clib_intf.file_map['TEST'] == '/file/name'

        parser = CParser()
        parser.read(open(test_filename))
        assert parser.clib_intf.file_map['TEST'] == test_filename

        parser = CParser()
        parser.read(io.StringIO('#define TEST 1'))
        assert parser.clib_intf.file_map['TEST'] is None

        parser = CParser()
        parser.read(io.StringIO('#define TEST 1'),
                    virtual_filename='/file/name')
        assert parser.clib_intf.file_map['TEST'] == '/file/name'


class TestPreprocessing(object):
    """Test preprocessing.

    """

    def setup(self):
        this_dir = os.path.dirname(__file__)
        self.parser = CParser(header_dirs=[
            os.path.join(this_dir, H_DIRECTORY, 'macros')])

    def test_invalid_define(self):
        with raises(err.DefinitionError):
            self.parser.read('macro_invalid.h')

    def test_values(self):
        self.parser.read('macro_values.h')

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

    def test_conditionals(self):
        preproc_srccode_fileobj = io.StringIO()
        self.parser.read('macro_conditionals.h',
                         preproc_out_file=preproc_srccode_fileobj)

        macros = self.parser.clib_intf.macros
        stream = preproc_srccode_fileobj.getvalue()

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
        preproc_srccode_fileobj = io.StringIO()
        self.parser.read('macro_functions.h',
                         preproc_out_file=preproc_srccode_fileobj)

        values = self.parser.clib_intf.macro_vals
        macros = self.parser.clib_intf.macros
        stream = preproc_srccode_fileobj.getvalue()

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
        this_dir = os.path.dirname(__file__)
        path = os.path.join(this_dir, H_DIRECTORY, 'macros/pragmas.h')
        pack_list = []
        srccode = self.parser.remove_comments(open(path).read())
        preproc_srccode = self.parser.preprocess(srccode, pack_list=pack_list)

        # Check if no line was removed/added to ensure that lineno references
        # are correct
        assert preproc_srccode.count('\n') == srccode.count('\n')

        # Check all pragmas instructions have been removed.
        assert preproc_srccode.strip() == ''

        assert pack_list == [
            (0, None),
            (17, None),
            (20, 4),
            (24, 16),
            (27, None),
            (30, None),
            (31, 4),
            (34, 16),
            (35, None)]

class TestParsing(object):
    """Test parsing.

    """

    def setup(self):
        this_dir = os.path.dirname(__file__)
        hdr_dir = os.path.join(this_dir, H_DIRECTORY)
        self.parser = MSVCParser(header_dirs=[hdr_dir])
        self.clib_intf = self.parser.clib_intf

    def test_variables(self):
        self.parser.read('variables.h')
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

        assert '$ms_type_qual_test' in vars

    # No structure, no unions, no enum
    def test_typedef(self):
        self.parser.read('typedefs.h')

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

    def test_enums(self):
        self.parser.read('enums.h')

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
        self.parser.read('structs.h')

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
        self.parser.read('unions.h')

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

    def test_functions(self):
        self.parser.read('functions.h')

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

        assert (funcs['array_param_func'] ==
                cm.FunctionType(cm.BuiltinType('void'), [
                    ('arr_params', cm.ArrayType(
                        cm.BuiltinType('int'), None))]))


class TestMSVCParser(object):

    def test_extended_types(self):
        srccode = """
            __int64 int64;
            unsigned __int64 int64_un;
        """
        std_parser = CParser()
        std_parser.read(io.StringIO(srccode))
        assert not isinstance(std_parser.clib_intf['int64'], cm.BuiltinType)

        ms_parser = MSVCParser()
        ms_parser.read(io.StringIO(srccode))
        assert ms_parser.clib_intf['int64'] == cm.BuiltinType('__int64')
        assert (ms_parser.clib_intf['int64_un'] ==
                cm.BuiltinType('unsigned __int64'))

    def test_extended_typequals(self):
        srccode = """
            int __w64 w64;
        """
        std_parser = CParser()
        std_parser.read(io.StringIO(srccode))
        assert not isinstance(std_parser.clib_intf['w64'], cm.BuiltinType)

        ms_parser = MSVCParser()
        ms_parser.read(io.StringIO(srccode))
        assert (ms_parser.clib_intf['w64'] ==
                cm.BuiltinType('int', quals=['__w64']))

    def test_extended_storage_classes(self):
        srccode = """
            int __declspec(dllexport) exp_int;
            int __inline inline_func();
        """
        std_parser = CParser()
        std_parser.read(io.StringIO(srccode))
        assert (std_parser.clib_intf.storage_classes.get('exp_int') !=
                ['__declspec(dllexport)'])
        assert (std_parser.clib_intf.storage_classes.get('inline_func') !=
                ['__inline'])

        ms_parser = MSVCParser()
        ms_parser.read(io.StringIO(srccode))
        assert (ms_parser.clib_intf.storage_classes['exp_int'] ==
                ['__declspec(dllexport)'])
        assert (ms_parser.clib_intf.storage_classes['inline_func'] ==
                ['__inline'])

    def test_extended_idents(self):
        srccode = """
            #define $X$ $y$
            int $X$;
        """
        std_parser = CParser()
        with raises(DefinitionError):
            std_parser.read(io.StringIO(srccode))

        ms_parser = MSVCParser()
        ms_parser.read(io.StringIO(srccode))
        assert ms_parser.clib_intf['$y$'] == cm.BuiltinType('int')

    def test_predefined_macros(self):
        std_parser = CParser()
        assert std_parser.clib_intf.macros['__STDC__'].content == '1'
        assert '_MSC_VER' not in std_parser.clib_intf.macros

        ms_parser = MSVCParser(msc_ver=1500, arch=64)
        assert std_parser.clib_intf.macros['__STDC__'].content == '1'
        assert ms_parser.clib_intf.macros['_MSC_VER'].content == '1500'
        assert ms_parser.clib_intf.macros['_M_AMD64'].content == ''
