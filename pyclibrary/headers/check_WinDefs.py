# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""After changing the parser this script should be used, if reading the
windows header files return the same results.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from pyclibrary.c_parser import CParser
from pyclibrary.c_model import CLibInterface, FnMacro
from pyclibrary.utils import add_header_locations
import os
import time

SDK_DIR = r'c:\program files\microsoft sdks\windows\v6.0a\include'

def load_cached_win_defs():
    this_dir = os.path.dirname(__file__)
    parser = CParser()
    parser.load_cache(os.path.join(this_dir, 'WinDefs.cache'))
    return parser

def generate_win_defs(version='1500'):
    header_files = ['specstrings.h', 'specstrings_strict.h', 'Rpcsal.h',
                    'WinDef.h', 'BaseTsd.h', 'WTypes.h',
                    'WinNt.h', 'WinBase.h', 'WinUser.h']
    clib_intf = CLibInterface()
    clib_intf.add_macro('DECLARE_HANDLE',
                        FnMacro('typedef HANDLE name', ['name']))
    parser = CParser(
        header_files,
        clib_intf,
        process_all=False,
        _WIN32='',
        _MSC_VER=version,
        _M_IX86='',   # must be _M_AMD64 in 64bit systems
        NO_STRICT='',
        )

    parser.process_all()
    return parser

if __name__ == "__main__":
    add_header_locations([SDK_DIR])

    ok_parser = load_cached_win_defs()
    print('parsing windows definitions (may take some while)')
    start_time = time.time()
    chk_parser = generate_win_defs()
    print('required time: {:1.3f}'.format(time.time()-start_time))

    for objtypename, ok_objmap in ok_parser.clib_intf.obj_maps.items():
        chk_objmap = chk_parser.clib_intf.obj_maps[objtypename]

        if ok_objmap.keys() != chk_objmap.keys():
            print(objtypename,'differs')
            missing = set(ok_objmap) - set(chk_objmap)
            unknown = set(chk_objmap) - set(ok_objmap)
            if missing or unknown:
                if missing:
                    print('    missing:', ', '.join(missing))
                if unknown:
                    print('    unknown:', ', '.join(unknown))
            print()

    common_stors = (set(ok_parser.clib_intf.storage_classes) &
                    set(chk_parser.clib_intf.storage_classes))
    for stor_name in common_stors:
        ok_stor_cls = ok_parser.clib_intf.storage_classes[stor_name]
        chk_stor_cls = chk_parser.clib_intf.storage_classes[stor_name]
        if chk_stor_cls != ok_stor_cls:
            print('storage classes of', stor_name, 'differs')
            if ok_stor_cls is None:
                continue
            missing = set(ok_stor_cls) - set(chk_stor_cls)
            unknown = set(chk_stor_cls) - set(ok_stor_cls)
            if missing or unknown:
                if missing:
                    print('    missing:', missing)
                if unknown:
                    print('    unknown:', unknown)
