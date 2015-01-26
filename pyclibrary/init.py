# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Initialisation routines.

Those should be run before creating a CParser and can be run only once. They
are used to declare additional types and modifiers for the parser.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
import sys
from ctypes import c_longlong
from .c_parser import _init_cparser, CParser
from .c_library import _init_clibrary, CLibrary


def init(extra_types={}, extra_modifiers=[]):
    """Init CParser and CLibrary classes.

    Parameters
    ----------
    extra_types : dict
        typeName->c_type pairs to extend typespace.
    extra_modifiers : list
        List of modifiers, such as '__stdcall'.

    """
    if CParser._init or CLibrary._init:
        raise RuntimeError('Can only initialise the parser once')

    _init_cparser(extra_types.keys(), extra_modifiers)
    _init_clibrary(extra_types)

    CParser._init = True
    CLibrary._init = True


WIN_TYPES = {'__int64': c_longlong}
WIN_MODIFIERS = ['__based', '__declspec', '__fastcall',
                 '__restrict', '__sptr', '__uptr', '__w64',
                 '__unaligned', '__nullterminated']


def auto_init(os=None, extra_types={}, extra_modifiers=[]):
    """Init CParser and CLibrary classes based on the targeted OS.

    Parameters
    ----------
    os : {'win32', 'linux2', 'darwin'}, optional
        OS for which to prepare the system. If not specified sys is used to
        identify the OS.
    extra_types : dict, optional
        Extra typeName->c_type pairs to extend typespace.
    extra_modifiers : list, optional
        List of extra modifiers, such as '__stdcall'.

    """
    if sys.platform == 'win32':
        extra_types.update(WIN_TYPES)
        extra_modifiers += WIN_MODIFIERS

        init(extra_types, extra_modifiers)
