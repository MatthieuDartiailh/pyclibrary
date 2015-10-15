# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
import io

import pytest

from pyclibrary.backends.pep8_formatter import Pep8Formatter
from pyclibrary.backends.code_layouter import CodeLayouter
import pyclibrary.asts.python as py


class TestPep8Format(object):

    def assertLayout(self, ast, textRepr, flavour='py3'):
        outFile = io.StringIO()
        with CodeLayouter(outFile) as cl:
            Pep8Formatter(cl, flavour).transform(ast)
        assert outFile.getvalue() == textRepr

    def test_UnknownType_raisesUnsupportedClassError(self):
        with pytest.raises(Pep8Formatter.UnsupportedClassError):
            self.assertLayout(py.PyAstNode, '')

    def test_IdFmt_ok(self):
        self.assertLayout(
            py.Id('test'),
            'test')

    def test_Str_ok(self):
        self.assertLayout(
            py.Str('test'),
            repr('test'))

    def test_Int_ok(self):
        self.assertLayout(
            py.Int(44),
            '44')

    def test_BinaryOp_ok(self):
        self.assertLayout(
            py.Add(py.Id('test1'), py.Id('test2')),
            'test1 + test2')

    def test_ClassDefFmt_onEmptyClassDef(self):
        self.assertLayout(
            py.ClassDef('test'),
            "class test:\n"
            "    pass\n")

    def test_ClassDefFmt_onHasParentClasses(self):
        self.assertLayout(
            py.ClassDef('test', [py.Id('parent1'), py.Id('parent2')]),
            "class test(parent1, parent2):\n"
            "    pass\n")

    def test_ClassDefFmt_onHasStatments(self):
        self.assertLayout(
            py.ClassDef('test', [], [
                py.Assign(py.Id('attr1'), py.Int(1)),
                py.Assign(py.Id('attr2'), py.Int(33))]),
            "class test:\n"
            "\n"
            "    attr1 = 1\n"
            "\n"
            "    attr2 = 33\n")
