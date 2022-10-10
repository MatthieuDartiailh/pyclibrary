# -----------------------------------------------------------------------------
# Copyright 2015-2022 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
import logging
logging.getLogger('pyclibrary').addHandler(logging.NullHandler())

from .c_parser import win_defs, CParser
from .c_library import CLibrary, build_array, cast_to
from .errors import DefinitionError
from .init import init, auto_init
