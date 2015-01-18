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
from pyclibrary.c_parser import CParser


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


class TestMacroParsing(object):
    """Test macro preprocessing.

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

        assert ('MACRO_D1' in macros and macros['MACRO_D1'] == '1' and
                values['MACRO_D1'] == 1)
        assert ('MACRO_D2' in macros and macros['MACRO_D2'] == '2U' and
                values['MACRO_D2'] == 2)
        assert ('MACRO_D3' in macros and macros['MACRO_D3'] == '3UL' and
                values['MACRO_D3'] == 3)

        assert ('MACRO_SD1' in macros and
                macros['MACRO_SD1'] == '(1 << 1)' and
                values['MACRO_SD1'] == 2)
        assert ('MACRO_SD2' in macros and
                macros['MACRO_SD2'] == '(2U << 2)' and
                values['MACRO_SD2'] == 8)
        assert ('MACRO_SD3' in macros and
                macros['MACRO_SD3'] == '(3UL << 3)' and
                values['MACRO_SD3'] == 24)

        assert ('MACRO_H1' in macros and
                macros['MACRO_H1'] == '0x000000' and
                values['MACRO_H1'] == 0)
        assert ('MACRO_H2' in macros and
                macros['MACRO_H2'] == '0x000001U' and
                values['MACRO_H2'] == 1)
        assert ('MACRO_H3' in macros and
                macros['MACRO_H3'] == '0X000002UL' and
                values['MACRO_H3'] == 2)

        assert ('MACRO_SH1' in macros and
                macros['MACRO_SH1'] == '(0x000000 << 1)' and
                values['MACRO_SH1'] == 0)
        assert ('MACRO_SH2' in macros and
                macros['MACRO_SH2'] == '(0x000001U << 2)' and
                values['MACRO_SH2'] == 4)
        assert ('MACRO_H3' in macros and
                macros['MACRO_SH3'] == '(0X000002UL << 3)' and
                values['MACRO_SH3'] == 16)

        assert ('MACRO_F1' in macros and
                macros['MACRO_F1'] == '1.0' and
                values['MACRO_F1'] == 1.0)
        assert ('MACRO_F2' in macros and
                macros['MACRO_F2'] == '1.1e1' and
                values['MACRO_F2'] == 11.)
        assert ('MACRO_F3' in macros and
                macros['MACRO_F3'] == '-1.1E-1' and
                values['MACRO_F3'] == -0.11)

        assert ('MACRO_S' in macros and macros['MACRO_S'] == '"test"' and
                values['MACRO_S'] == 'test')

        assert ('NESTED' in macros and macros['NESTED'] == '1' and
                values['NESTED'] == 1)
        assert ('NESTED2' in macros and macros['NESTED2'] == '1' and
                values['NESTED2'] == 1)
        assert 'MACRO_N' in macros and macros['MACRO_N'] == '1 2'

    def test_macro_function(self):

        pass

    def test_conditionals(self):

        pass

    def test_pragmas(self):

        pass


class TestEnumParsing(object):

    def setup(self):

        pass

    def test_enum_parsing(self):

        pass


class TestTypedefParsing(object):

    def setup(self):

        pass
