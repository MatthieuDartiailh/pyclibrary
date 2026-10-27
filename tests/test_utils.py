# -----------------------------------------------------------------------------
# Copyright 2015-2025 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test the utility functions."""

import os
import sys

from pyclibrary.utils import find_header


def test_find_header_in_linux_system_dirs(monkeypatch):
    """Test that the system include directories are searched on Linux."""
    monkeypatch.setattr(sys, "platform", "linux")
    header = os.path.join("/usr/include", "pyclib_test.h")
    monkeypatch.setattr(os.path, "isfile", lambda path: path == header)
    assert find_header("pyclib_test.h") == header
