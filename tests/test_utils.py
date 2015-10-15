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
from pyclibrary import utils
import pyclibrary.asts.astcore


class TestDataObject(object):

    class DummyObj(pyclibrary.asts.astcore.AstNode):
        __slots__ = ('p1', 'p2', 'p3', 'p4')

    def test_autoCreatedInit_doesNotCreateDict(self):
        class TCls(pyclibrary.asts.astcore.AstNode): __slots__ = ('param',)
        tobj = TCls(1)
        assert not '__dict__' in dir(tobj)

    def test_autoCreatedInit_onPositionalArgs_setsParams(self):
        class TCls(pyclibrary.asts.astcore.AstNode): __slots__ = ('p1', 'p2')
        tobj = TCls(1, 2)
        assert tobj.p1 == 1 and tobj.p2 == 2

    def test_autoCreatedInit_onKeywordArgs_setsParams(self):
        class TCls(pyclibrary.asts.astcore.AstNode): __slots__ = ('p1', 'p2')
        tobj = TCls(p1=1, p2=2)
        assert tobj.p1 == 1 and tobj.p2 == 2

    def test_autoCreatedInit_onTooLessArgs_raisesTypeError(self):
        class TCls(pyclibrary.asts.astcore.AstNode): __slots__ = ('p1', 'p2', 'p3')
        with pytest.raises(TypeError):
            TCls(1, p2=2)

    def test_autoCreatedInit_onTooMuchPositionalArgs_raisesTypeError(self):
        class TCls(pyclibrary.asts.astcore.AstNode): __slots__ = ('p1',)
        with pytest.raises(TypeError):
            TCls(1, 2)

    def test_autoCreatedInit_onUnknownKeywordArgs_raisesTypeError(self):
        class TCls(pyclibrary.asts.astcore.AstNode): __slots__ = ('p1',)
        with pytest.raises(TypeError):
            TCls(p1=1, p2=2)

    def test_autoCreatedInit_mixedPosAndKwdArgs_setsParams(self):
        class TCls(pyclibrary.asts.astcore.AstNode): __slots__ = ('p1', 'p2')
        tobj = TCls(1, p2=2)
        assert tobj.p1 == 1 and tobj.p2 == 2

    def test_autoCreateInit_onDerivedCls_combinesPositionArgList(self):
        class Parent(pyclibrary.asts.astcore.AstNode): __slots__ = ('p3', 'p4')
        class Child(Parent): __slots__ = ('p1', 'p2')
        obj = Child(1, 2, 3, 4)
        assert obj.p1 == 1, obj.p2 == 2 and obj.p3 == 3 and obj.p4 == 4

    def test_autoCreateInit_onDerivedCls_forwardsKeywordArgs(self):
        class Parent(pyclibrary.asts.astcore.AstNode): __slots__ = ('p3', 'p4')
        class Child(Parent): __slots__ = ('p1', 'p2')
        obj = Child(p4=4, p1=1, p3=3, p2=2)
        assert obj.p1 == 1, obj.p2 == 2 and obj.p3 == 3 and obj.p4 == 4

    def test_autoCreateInit_onMixWithManualInit_ok(self):
        class Parent(object):
            __slots__ = ('p2',)
            def __init__(self, p2): self.p2 = p2
        class Child(Parent, pyclibrary.asts.astcore.AstNode): __slots__ = ('p1',)
        obj = Child(1, 2)
        assert obj.p1 == 1 and obj.p2 == 2

    def test_autoCreatedInit_onSlotsDefined_addsEmptySlots(self):
        class TCls(pyclibrary.asts.astcore.AstNode): pass
        tobj = TCls()
        assert not '__dict__' in dir(tobj)

    def test_repr(self):
        class TCls(pyclibrary.asts.astcore.AstNode): __slots__ = ('p1', 'p2')
        assert repr(TCls(1, 2)) == "TCls(1, 2)"

    def test_repr_onDerivedCls(self):
        class Parent(pyclibrary.asts.astcore.AstNode): __slots__ = ('p3', 'p4')
        class Child(Parent): __slots__ = ('p1', 'p2')
        assert repr(Child(1, 2, 3, 4)) == "Child(1, 2, 3, 4)"

    def test_eq_onEqualParams_returnsTrue(self):
        assert self.DummyObj(0, [], 0, 0) == self.DummyObj(0, [], 0, 0)
        assert (self.DummyObj(3, ['test', 'test2'], 'test3', [9]) ==
                self.DummyObj(3, ['test', 'test2'], 'test3', [9]))

    def test_ne_onDifferentParams_returnsTrue(self):
        assert self.DummyObj(0, [], 0, 0) != self.DummyObj(0, [], 0, 1)
        assert self.DummyObj(0, [], 0, 0) != self.DummyObj(0, ['test'], 0, 0)
        assert (self.DummyObj(0, [], 0, 0) !=
                self.DummyObj(0, [], p3='test', p4=0))

    def test_ne_onOtherType_returnsTrue(self):
        class OtherDummyObj(pyclibrary.asts.astcore.AstNode):
            __slots__ = ('p1', 'p2', 'p3', 'p4')
        assert self.DummyObj(0, 0, 0, 0) != OtherDummyObj(0, 0, 0, 0)

    def test_copy(self):
        orig_obj = self.DummyObj(3, ['test'], 'test2', [9])
        copied_obj = orig_obj.copy()
        assert orig_obj == copied_obj
        assert orig_obj is not copied_obj
        assert orig_obj.p2 is copied_obj.p2

