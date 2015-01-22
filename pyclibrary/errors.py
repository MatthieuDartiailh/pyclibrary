# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Errors that can happen during parsing or binding.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)


class PyCLibError(Exception):
    """Base exception for all PyCLibrary exceptions.

    """
    pass


class DefinitionError(PyCLibError):
    """Excepion signaling that one definition found in the header is malformed
    or meaningless.

    """
    pass
