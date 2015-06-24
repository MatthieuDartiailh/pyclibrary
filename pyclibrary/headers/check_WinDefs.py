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
from pyclibrary.c_parser import CParser, win_defs
from pyclibrary.utils import add_header_locations
import os
import time

SDK_DIR = r'c:\program files\microsoft sdks\windows\v6.0a\include'
HEADER_FILES = ['SpecStrings.h', 'WinNt.h', 'WinDef.h', r'WinBase.h',
                'BaseTsd.h', 'WTypes.h', 'WinUser.h']

def load_cached_win_defs():
    this_dir = os.path.dirname(__file__)
    parser = CParser()
    parser.load_cache(os.path.join(this_dir, 'WinDefs.cache'))
    return parser

def generate_win_defs(version='1500'):
    parser = CParser(
        HEADER_FILES,
        process_all=False,
        _WIN32='',
        _MSC_VER=version,
        CONST='const',
        NO_STRICT=None,  ### not needed?
        MS_WIN32='',  ### not needed?
        )

    parser.process_all()
    return parser

def main():
    ok_parser = load_cached_win_defs()
    print('parsing windows definitions (may take some while)')
    start_time = time.time()
    chk_parser = generate_win_defs()
    print('required time: {:1.3f}'.format(time.time()-start_time))

    for objtypename, ok_objmap in ok_parser.clib_intf.obj_maps.items():
        chk_objmap = chk_parser.clib_intf.obj_maps[objtypename]
        if ok_objmap != chk_objmap:
            missing = set(ok_objmap) - set(chk_objmap)
            unknown = set(chk_objmap) - set(ok_objmap)
            if missing or unknown:
                print(objtypename,'differs:')
                if missing:
                    print('    missing:', missing)
                if unknown:
                    print('    unknown:', unknown)

if __name__ == "__main__":
    add_header_locations([SDK_DIR])
    main()