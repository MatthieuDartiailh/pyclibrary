# PyClibrary

[![Build Status](https://travis-ci.org/MatthieuDartiailh/pyclibrary.svg?branch=master)](https://travis-ci.org/MatthieuDartiailh/pyclibrary)
[![Coverage Status](https://coveralls.io/repos/MatthieuDartiailh/pyclibrary/badge.svg?branch=master)](https://coveralls.io/r/MatthieuDartiailh/pyclibrary?branch=master)
[![Documentation Status](https://readthedocs.org/projects/pyclibrary/badge/?version=latest)](https://readthedocs.org/projects/pyclibrary/?badge=latest)
[![Latest Version](https://pypip.in/version/pyclibrary/badge.svg)](https://pypi.python.org/pypi/pyclibrary/)
[![Downloads](https://pypip.in/download/pyclibrary/badge.svg)](https://pypi.python.org/pypi/pyclibrary/)
[![Supported Python versions](https://pypip.in/py_versions/pyclibrary/badge.svg)](https://pypi.python.org/pypi/pyclibrary/)
[![Wheel Status](https://pypip.in/wheel/pyclibrary/badge.svg)](https://pypi.python.org/pypi/pyclibrary/)
[![License](https://pypip.in/license/pyclibrary/badge.svg)](https://pypi.python.org/pypi/pyclibrary/)

C parser and bindings automation for Python.

Fork of https://launchpad.net/pyclibrary.

PyCLibrary includes 1) a pure-python C parser and 2) an automation library
that uses C header file definitions to simplify the use of c bindings. The
C parser currently processes all macros, typedefs, structs, unions, enums,
function prototypes, and global variable declarations, and can evaluate
typedefs down to their fundamental C types + pointers/arrays/function
signatures. Pyclibrary can automatically build c structs/unions and perform
type conversions when calling functions via cdll/windll.

PyCLibrary tries to present a ffi agnostic API to allow using different
bindings. For the time being only the ctypes based backend is implemented but
a cffi backend should be possible to implement (the rational for it would be
that the CParser can be used on raw header files which are not always well
supported by the cffi parser).

However if you need to manipulate the C object coming back from the library
which cannot simply be mapped to Python object your code will most likely
not be backend independent so it is discouraged to try to switch between
backends.
