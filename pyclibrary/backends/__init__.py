# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""
"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from .ctypes import (init_clibrary as c_init,
                     identify_library as c_iden,
                     get_library_path as cpath)

lib_types = {'ctypes': c_iden}
lib_path = {'ctypes': cpath}


def identify_library(lib):
    """Identify a library backend.

    """
    for typ, check in lib_types.items():
        if check(lib):
            return typ


def get_library_path(lib, backend=None):
    """Retrieve the path to the dynamic library file.

    """
    if not backend or backend not in lib_path:
        backend = identify_library(lib)

    return lib_path[backend](lib)


def init_libraries(extra_types):
    """Run the initialiser of each backend.

    """
    c_init(extra_types)
