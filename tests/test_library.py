# -----------------------------------------------------------------------------
# Copyright 2015-2025 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test of the generic wrapper library capabilities.

This actually needs ctypes to make sense but it affects all wrappers.

"""

import _ctypes_test
import ctypes
import os

import pytest
from pyclibrary.c_library import CLibrary
from pyclibrary.utils import (
    HEADER_DIRS,
    LIBRARY_DIRS,
    add_header_locations,
    add_library_locations,
)

HEADERS_DIR = os.path.dirname(__file__)
BACKUPS = ()


def setup_module():
    global BACKUPS
    BACKUPS = HEADER_DIRS[:]
    add_header_locations([os.path.join(os.path.dirname(__file__), "headers")])


def teardown_module():
    global HEADER_DIRS
    if BACKUPS:
        HEADER_DIRS = BACKUPS


@pytest.fixture
def library_location_fixture():
    global LIBRARY_DIRS
    old = LIBRARY_DIRS[:]
    add_library_locations([os.path.dirname(_ctypes_test.__file__)])
    yield
    LIBRARY_DIRS = old


class TestCLibrary(object):
    """Test the basic CLibrary object functionalities."""

    def test_accessing_library_by_name(self, library_location_fixture):
        library = CLibrary(os.path.basename(_ctypes_test.__file__), ["ctypes_test.h"])
        assert library._lib_

    def test_accessing_library_by_path(self):
        library = CLibrary(_ctypes_test.__file__, ["ctypes_test.h"])
        assert library._lib_

    def test_accessing_library_by_object(self):
        CLibrary.libs.clear()
        lib = ctypes.CDLL(_ctypes_test.__file__)
        library = CLibrary(lib, ["ctypes_test.h"])
        assert library._lib_ is lib

    def test_already_opened_library(self):
        lib = ctypes.CDLL(_ctypes_test.__file__)
        library = CLibrary(lib, ["ctypes_test.h"])
        assert library is CLibrary(_ctypes_test.__file__, ["ctypes_test.h"])

    def test_accessing_prefixed_value(self):
        pass


def test_function_pretty_signature():
    """Test building the pretty signature of a function."""
    library = CLibrary(os.path.basename(_ctypes_test.__file__), ["ctypes_test.h"])
    library.my_strdup.pretty_signature()
