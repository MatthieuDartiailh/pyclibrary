# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test version script (avoid stupid mistakes).

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from pyclibrary.version import __version__


def test_version():
    assert __version__
