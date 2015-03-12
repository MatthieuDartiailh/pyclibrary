Welcome to PyCLibrary's documentation!
======================================

PyCLibrary tries to make wrapping dynamic librariries in python less cumbersome
and more user friendly.

The idea is that most of the things needed such as constant values and function
signatures are already presents in the headers files of the library (which
are usually accessible as they are needed for using the library in C). So
better to use them than copy everything by hand.

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

PyCLibrary supports Python 2.7 and 3.3+

.. toctree::
    :hidden:

    Getting Started <get_started/index>
    Architecture Reference <arch_ref/index>
    FAQs <faqs/index>
    API Reference <api_ref/index>

- :doc:`get_started/index`

    How to set up PyCLibrary and make your first step with it.

- :doc:`arch_ref/index`

   More references on PyCLibrary internals.

- :doc:`faqs/index`

    Some questions that might have occurred to others too.

- :doc:`api_ref/index`

    When all else fails, consult the API docs to find the answer you need.
    The API docs also include convenient links to the most definitive
    PyCLibrary documentation: the source.
