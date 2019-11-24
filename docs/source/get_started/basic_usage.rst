.. _basic_usage:

Basic usage
===========

.. contents::

This guide tries to give a simple overview of PyCLibrary capabilities. At the
end it refers to C concepts as some basic knowledge of them might be necessary
when interfacing a C library but do not be scared by them. 

Parsing headers
---------------

The first step you should take when trying to interface with a dynamic library
using PyCLibrary is to check that it can correctly Parse the header files::

    >>> from pyclibrary import CParser
    >>> parser = CParser(['first_header_file_path','second_header_file_path'])
    >>> print(parser)
	
If the second command does not raise any issue it means that it successfully 
parsed the headers. However even in such a case the parser might have 
overlooked some definitions. The last command will print all the definitions 
extracted from the header files grouped by categories : 

- types : the custom types defined in the headers
- variables : the global variable of the libraries.
- fnmacros : the function macros declared in the headers (Those are used by 
  the compiler preprocessor and you have no reason to access them).
- macros : the macros defined in the headers.
- structs : the custom structures used by the libraries.
- unions : the customs unions used by the libraries.
- enums : the enumerations defined in the headers.
- functions : the functions you will be able to call.
- values : the global values you may need to access (mainly macro values 
  which are used to provide a more descriptive representation of integer
  values)
	
You can quickly go over them and check if something is missing.

.. note::
	On windows, it is generally a good idea to include some standards windows
	definition. To do so pass the result of calling the win_defs function to
	the parser as second argument (copy_from keyword).

.. note::
    The :py:class:`CParser <pyclibrary.c_parser.CParser>` does not handle the
    include directive (for the time being) so you must pass all the header 
    files.
	
Caching the parsed files
^^^^^^^^^^^^^^^^^^^^^^^^

As parsing the headers is a fairly expensive process, it is a good idea to
cache the parsed definition.

To cache definitions, you simply have to provide a path pointing to the file 
in which to save the parsed definitions to the parser (cache keyword). If the
cache file already exists, it is loaded only if the version of the parser
matches (which allows update to always take effects) and if the arguments 
passed to the :py:class:`CParser <pyclibrary.c_parser.CParser>` are the same 
(if you ask for different replacements in your file it will trigger a 
re-parsing).

The previous procedure should be sufficient in general but in some cases you
might want a finer control on the parsing procedure. See for a more detailed 
explanation.

Binding the library
-------------------

Once you know that you can correctly parse the headers of your library, you are
ready to bind it. To do so, you must create a 
:py:class:`CLibrary <pyclibrary.c_library.CLibrary>` object::

	>>> from pyclibrary import CLibrary
	>>> clib = CLibrary('mylibrary.dll', parser, prefix='Lib_', 
    >>>                 lock_calls=False, convention='cdll', backend='ctypes')

In order to work, the :py:class:`CLibrary <pyclibrary.c_library.CLibrary>`
needs the name or the path to the library to use (a .dll on Windows, a .so on 
Linux), and either an initialized parser or a list of header files which will 
be parsed for definitions. When you provide simply  name of the library it is 
looked for in standard locations according to your OS. All other keyword 
arguments are optionals : 

- prefix : 
    prefix or list of prefix often found in the library function or 
    attributes names. This allow you to access to them without the prefix, 
    while not preventing to use the complete name.
- lock_calls : 
    when this flag is set all calls to the dll are made thread
    safe by acquiring a lock before calling and releasing it after. This can 
    be useful if the library is not thread-safe.
- convention : 
    this only applies on windows platform where the calling convention can
    be either 'cdll' (Linux standard), windll or oledll. Note that all 
    conventions might not be supported on all platforms and with all
    backends.
- backend : 
    the name of the backend to use when binding to the library.
    Currently the only backend relies on the ctypes library, in the future 
    one using the cffi library might be used.

All other keyword arguments will be passed to when creating a 
:py:class:`CParser <pyclibrary.c_parser.CParser>` if a list of headers files 
is passed.
	
You now have access to all the attributes, types and functions defined by the
library.
	
Accessing attributes
^^^^^^^^^^^^^^^^^^^^

The preferred way to access library attributes is simply by using the . 
syntax::

	>>> clib.HIGH_FLAG
	1
	
This simply looked for into all the known definition for a HIGH_FLAG value or
Lib_HIGH_FLAG value as we specified 'Lib\_' as a prefix. This will work for 
values, functions, types, structures, unions, enumerations but not for macros
definitions.

But you can also specify what kind of object you are looking for using the 
following syntax::
	
	>>> clib('values', 'HIGH_FLAG')
	1
	
The recognized values for the first argument are the following : 'values', 
'functions', 'types', 'structs', 'unions', or 'enums'. This method is roughly 
equivalent to the first one. It is however useful if for example one needs to 
access to an enumeration type : when looking for it the entries found in values
which specifies the mapping between names and their integer value is always 
found first (as it is most of the time what is useful), so if you want the type
you need to specify it explicitly.

The third way gives access directly to the parser definitions::

	>>>clib['values']['HIGH_FLAG']
	1
	
This is equivalent to doing::

	>>>parser.defs['values']['HIGH_FLAG']

Calling functions
^^^^^^^^^^^^^^^^^

One usual behavior of C function is to return a kind of flag signaling that 
the operation while returning the real values of interest by updating pointers
which have been passed to them. Most of the time those pointer does not need
to be initialized to any particular value and it is often tedious to create
them. PyCLibrary tries to make that kind of things easier. Here are some of the
key concept used :

- function always return a 
  :py:class:`CallResult <pyclibrary.c_library.CallResult>` object which 
  encapsulates the return value of the function and all the arguments passed to
  it.
- when calling a function you can use keyword arguments based on the C
  signature of the function.
- you can omit all uninitialized pointers the function expects, PyCLibrary
  will create them for you and they will be accessible in the
  :py:class:`CallResult <pyclibrary.c_library.CallResult>`
  object.
	
Let's consider a C function whose signature is the following :

.. code-block:: c

	RETURN_CODE get_library_version(U8 *Major,U8 *Minor,U8 *Revision);
	
Once wrapped by PyCLibrary this function can be called as follows::

	>>> ret = clib.get_library_version()
	>>> ret()
	1  # This is the RETURN_CODE value, 1 means the call succeeded
	>>> ret[0]
	0  # This is the major version.
	>>> ret['Minor']
	1
	
Some explanations :

- first we call the function, not providing any pointers and store the 
  CallResult object.
- then we query the return value by calling the 
  :py:class:`CallResult <pyclibrary.c_library.CallResult>` object. 
  When doing this PyCLibrary tries to convert the value to a nice Python 
  equivalent and if it is not possible it returns the underlying backend
  object.
- finally we access to the major and minor version info. To access to the
  major version info we query the argument using its index, for the minor
  we use the name of the argument. 
	
Sometimes even if a Python equivalent exists you might need to access to raw 
backend objects. You can find it in the attribute 
:py:attr:`CallResult.rval <pyclibrary.c_library.CallResult.rval>`
for the return value and in 
:py:attr:`CallResult.rval <pyclibrary.c_library.CallResult.args>`  for the 
argument (that you passed and the created pointers).

Note that all the pointers automatically created by PyCLibrary are dereferenced 
automatically so that you get the value to which they point to, when accessed
through the '[]' operation, or using tuple unpacking see below.
    
As this syntax is not always convenient when we need to proceed to many calls
the :py:class:`CallResult <pyclibrary.c_library.CallResult>` object can be 
used as an iterator to allow unpacking::

	>>> res, (major, minor, rev) = clib.get_library_version()
	>>> '{}.{}.{}'.format(major, minor, rev)
	'0.1.0'
	
Note that the arguments are unpacked as a tuple (actually a generator) which 
makes it easy to ignore it if the function directly return the value you want::
	
	>>> val, _ = clib.get_value()
	2
	
.. note::

	The value auto-generated are pointers but are not returned as such because
	most of the time it is the stored value that is needed. For pointers of 
	pointers which generally represents arrays, it dereference only the 
	external pointer so that the array element can be accessed using pointer[i]
	(which is a valid C syntax).
	This magic happens only with auto-generated values, if you manually pass a
	pointer the value in the arguments will be a pointer.

Creating and passing arrays
^^^^^^^^^^^^^^^^^^^^^^^^^^^

One special case of passing values by reference (ie using a pointer) is the
case of the arrays. Here two solutions exist depending on the behavior of the
library :

- the function expects a pointer to pointer and handles itself the memory
  allocation.
- the function expects a pointer to an already existing array, and will use
  it or modify it.

In the first case, you can let PyCLibrary handle everything, you will get a 
pointer that you can index like any iterable (but you can't determine its 
length, you must get that information from the library in another way). In the
second case you cannot just let PyCLibrary creates the pointer because when 
the function will write in the array it might access memory it should not and 
corrupt data because the memory was never allocated. For this case, PyCLibrary
provides the :py:func:`build_array <pyclibrary.c_library.build_array>`
helper function. This function takes as arguments the library object, the type
of the data to store in the array (as a str or as type object) and the shape of
the array to build (multidimensional arrays are supported), and  optionally an
initialization iterable (for one dimensional arrays only).

Let's consider two functions:

.. code-block:: c

	void fill_array(int *array);
	void allocate_array(int size, int **array);
	
Note that without reading the docs, you cannot know that fill_array needs an 
array and not simply a pointer to an integer. You must read the docs !

And here it the interfacing code::

	>>> arr = build_array(clib, 'int', 5)
	>>> _, (arr) = fill_array(arr)
	>>> [arr[i] for i in range(5)]
	[0, 10, 20, 21, 55]
	>>> _, (size, arr) = allocate_array()
	>>> [arr[i] for i in range(size)]
	[-1, 2, 5, 8, -9]
	
This is fairly straightforward, simply note that you can directly pass the
array in place of a pointer, the backend handle the conversion.
