# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
import pytest
from pyclibrary.asts import astcore




def test_flatten_onEmptyIterator_returnsEmptyIterator():
    assert list(astcore.flatten(iter([]))) == \
           []


def test_flatten_onIterator_iterates():
    assert list(astcore.flatten(iter(['test']))) == \
           ['test']


def test_flatten_onNestedIterator_iterates():
    assert list(astcore.flatten(iter([iter(['test']), iter(['test2'])]))) == \
           ['test', 'test2']