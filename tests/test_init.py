# -----------------------------------------------------------------------------
# Copyright 2015-2022 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test init mechanisms."""

import pyclibrary.c_library as cl
import pyclibrary.c_parser as cp
import pytest
from pyclibrary.init import auto_init, init


@pytest.fixture
def init_fixture():
    cp.CParser._init = False
    cl.CLibrary._init = False
    yield


def test_init(init_fixture):
    init({"new_type": int}, ["__modifier"])
    assert "new_type" in cp.base_types
    assert cp.extra_modifier is not None
    from pyclibrary.backends.ctypes import CTypesCLibrary

    assert "new_type" in CTypesCLibrary._types_


def test_reinit_attempt(init_fixture):
    init()
    with pytest.raises(RuntimeError):
        init()


def test_auto_init(init_fixture):
    auto_init({"new_type": int}, ["__modifier"], "win32")
    assert "new_type" in cp.base_types
    assert "__int64" in cp.base_types
    assert cp.extra_modifier is not None
    from pyclibrary.backends.ctypes import CTypesCLibrary

    assert "new_type" in CTypesCLibrary._types_
    assert "__int64" in CTypesCLibrary._types_
