# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
""" Test of the generic wrapper library capabilities.

This actually needs ctypes to make sense but it affects all wrappers.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

import os
import _ctypes_test

from pyclibrary.utils import (add_header_locations, HEADER_DIRS)
from pyclibrary.c_library import CLibrary


BACKUPS = ()


def setup_module():
    global BACKUPS
    BACKUPS = HEADER_DIRS[:]
    add_header_locations([os.path.join(os.path.dirname(__file__),
                                       '..', 'headers')])


def teardown_module():
    global HEADER_DIRS
    if BACKUPS:
        HEADER_DIRS = BACKUPS


class TestCTypesCLibrary(object):
    """Test the ctypes wrapper functionality.

    """
    def setup(self):
        self.library = CLibrary(_ctypes_test.__file__, ['ctypes_test.h'])

    def test_call(self):
        pass

    def test_getattr(self):
        pass

    def test_getitem(self):
        pass

    def test_make_val(self):
        pass

    def test_make_type(self):
        pass

    def test_make_struct(self):
        pass

    def test_function_call1(self):
        res = self.library.get_an_integer()
        assert res() == 42

    def test_function_call2(self):
        res = self.library.getSPAMANDEGGS()
        assert res[0].name == 'first egg'
        assert res[0].num_spams == 1

    def test_extract_result(self):
        pass

    def test_to_pointer(self):
        pass

    def test_from_pointer(self):
        pass
