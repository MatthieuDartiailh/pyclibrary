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
import ctypes
import _ctypes_test
from pytest import raises

from pyclibrary.utils import (add_header_locations, HEADER_DIRS)
from pyclibrary.c_library import CLibrary, cast_to, build_array


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
        print(sorted(self.library._defs_['functions']))

    def test_call(self):
        point_cls = self.library('structs', 'tagpoint')
        point_cls(x=1, y=2)

        with raises(KeyError):
            self.library('r', 't')

    def test_getattr(self):
        assert self.library.an_integer == 42

    def test_getitem(self):
        assert self.library['values']['an_integer'] == 42

    def test_make_struct(self):
        self.library.BITS

    def test_function_call1(self):
        # Test calling a function taking no arguments.
        res = self.library.get_an_integer()
        assert res() == 42

    def test_function_call2(self):
        # Test calling a function without pointers.
        _, (res,) = self.library.getSPAMANDEGGS()
        egg = res[0]  # we get a pointer of pointer.
        # Needed because this is a byte array in python 3
        assert egg.name.decode('utf8') == 'first egg'
        assert egg.num_spams == 1
        assert egg.spams[0].name.decode('utf8') == 'name1'
        assert egg.spams[0].value.decode('utf8') == 'value1'
        assert egg.spams[1].name.decode('utf8') == 'name2'
        assert egg.spams[1].value.decode('utf8') == 'value2'

    def test_function_call3(self):
        # Test calling a function with an argument and a missing pointer.
        arg = self.library.point(x=1, y=2)
        res, (_, test_point) = self.library._testfunc_byval(arg)
        assert res == 3
        assert test_point.x == arg.x
        assert test_point.y == arg.y

    def test_function_call4(self):
        """Test calling a funcùtion returning a string

        Will fail if restype is not properly set.

        """
        test_str = 'Test'
        copy = self.library.my_strdup(test_str)()
        assert copy == test_str
        assert copy is not test_str

    def test_cast_to(self):
        """Test casting.

        """
        a = 10
        assert (cast_to(self.library, a, ctypes.c_void_p).value ==
                ctypes.cast(a, ctypes.c_void_p).value)

    def test_build_array(self):
        """Test array building.

        """
        pyc_array = build_array(self.library, ctypes.c_void_p, 2, [1, 2])
        c_array = (ctypes.c_void_p*2)(1, 2)
        assert type(pyc_array) == type(c_array)
        assert pyc_array[0] == c_array[0]
