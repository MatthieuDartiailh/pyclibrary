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
from pyclibrary.c_parser import MSVCParser
from pyclibrary.c_model import FnMacro
import os
import time

SDK_DIR = r'c:\program files\microsoft sdks\windows\v6.0a\include'

def load_cached_win_defs():
    this_dir = os.path.dirname(__file__)
    parser = MSVCParser(msc_ver=1500, arch=32, header_dirs=[SDK_DIR])
    parser.load_cache(os.path.join(this_dir, 'WinDefs.cache'),
                      check_validity=True)
    return parser

def generate_win_defs():
    parser = MSVCParser(header_dirs=[SDK_DIR],
                        predef_macros={'_WIN32': '', 'NO_STRICT': ''},
                        msc_ver=1500, arch=32)
    parser.clib_intf.add_macro(
        'DECLARE_HANDLE', FnMacro('typedef HANDLE name', ['name']))

    header_files = ['specstrings.h', 'specstrings_strict.h', 'Rpcsal.h',
                    'WinDef.h', 'BaseTsd.h', 'WTypes.h',
                    'WinNt.h', 'WinBase.h', 'WinUser.h']

    for header_file in header_files:
        parser.read(header_file)

    return parser

if __name__ == "__main__":
    ok_parser = load_cached_win_defs()
    print('parsing windows definitions (may take some while)')
    start_time = time.time()
    chk_parser = generate_win_defs()
    print('required time: {:1.3f}'.format(time.time()-start_time))

    for objtypename, ok_objmap in ok_parser.clib_intf.obj_maps.items():
        print('\n' + '-'*30, objtypename, '-'*30)
        chk_objmap = chk_parser.clib_intf.obj_maps[objtypename]

        missing = set(ok_objmap) - set(chk_objmap)
        unknown = set(chk_objmap) - set(ok_objmap)
        common = set(chk_objmap) & set(ok_objmap)

        if missing:
            print('missing:', ', '.join(missing))

        if unknown:
            print('added:', ', '.join(unknown))

        for objname in common:
            if ok_objmap[objname] != chk_objmap[objname]:
                print(objtypename, objname, ':',
                      repr(chk_objmap[objname]), '!=',
                      repr(ok_objmap[objname]))

            try:
                ok_stor = ok_parser.clib_intf.storage_classes[objname]
                chk_stor = chk_parser.clib_intf.storage_classes[objname]
            except KeyError:
                pass
            else:
                if ok_stor != chk_stor:
                    print('storage classes of', objtypename, objname, ':',
                          repr(chk_stor), '!=', repr(ok_stor))
