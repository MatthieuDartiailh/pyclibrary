# Taken from PyVisa cthelper.

import os
import sys

# On Linux, find Library returns the name not the path.
# This excerpt provides a modified find_library.
# noinspection PyUnresolvedReferences
if os.name == "posix" and sys.platform.startswith('linux'):

    # Andreas Degert's find functions, using gcc, /sbin/ldconfig, objdump
    def define_find_libary():
        import re
        import tempfile
        import errno

        def _findlib_gcc(name):
            expr = r'[^\(\)\s]*lib%s\.[^\(\)\s]*' % re.escape(name)
            fdout, ccout = tempfile.mkstemp()
            os.close(fdout)
            cmd = 'if type gcc >/dev/null 2>&1; then CC=gcc; else CC=cc; fi;' \
                  '$CC -Wl,-t -o ' + ccout + ' 2>&1 -l' + name
            trace = ''
            try:
                f = os.popen(cmd)
                trace = f.read()
                f.close()
            finally:
                try:
                    os.unlink(ccout)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise
            res = re.search(expr, trace)
            if not res:
                return None
            return res.group(0)

        def _findlib_ldconfig(name):
            # XXX assuming GLIBC's ldconfig (with option -p)
            expr = r'/[^\(\)\s]*lib%s\.[^\(\)\s]*' % re.escape(name)
            res = re.search(expr,
                            os.popen('/sbin/ldconfig -p 2>/dev/null').read())
            if not res:
                # Hm, this works only for libs needed by the python executable.
                cmd = 'ldd %s 2>/dev/null' % sys.executable
                res = re.search(expr, os.popen(cmd).read())
                if not res:
                    return None
            return res.group(0)

        def _find_library(name):
            path = _findlib_ldconfig(name) or _findlib_gcc(name)
            if path:
                return os.path.realpath(path)
            return path

        return _find_library

    find_library = define_find_libary()
else:
    from ctypes.util import find_library
