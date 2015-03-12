.. _basic_usage:

Basic usage
===========

.. contents::

Parsing headers
---------------

The first step you should take when trying to interface with a dynamic library
using PyCLibrary is to check that it can correctly Parse the header files : 

    >>>from pyclibrary import CParser
	>>>parser = CParser(['first_header_file_path','second_header_file_path'])
	>>>parser.print_all()
	
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
	
Caching the parsed files
^^^^^^^^^^^^^^^^^^^^^^^^

As parsing the headers is a fairly expensive process, it is a good idea to
cache the parsed definition.

To cache definitions, you simply have to provide a path pointing to the file 
in which to save the parsed definitions to the parser (cache keyword). If the
a cache file already exists, it is loaded only if the version of the parser
matches (which allows update to always take effects) and if the arguments 
passed to the CParser are the same (if you ask for different replacements in
your file it will trigger a re-parsing).

The previous procedure should be sufficient in general but in some cases you
might a finer control on the parsing procedure. See for a more detailed 
explanation.

Binding the library
-------------------

Once you know that you can correctly parse the headers of your library, you are
ready to bind it. To do so, you must create a CLibrary object :

	>>>from pyclibrary import CLibrary
	>>>clib = CLibrary('mylibrary.dll', parser, prefix='Lib_', 
					   lock_calls=False, convention='cdll', backend='ctypes')

In order to work the CLibrary needs the name or the path to the library to use
(a .dll on Windows, a .so on Linux), either an initialized parser or a list
of header files which will be parsed for definitions. All other keyword 
arguments are optionals : 
	- prefix : 
	
Accessing attributes
^^^^^^^^^^^^^^^^^^^^


Calling functions
^^^^^^^^^^^^^^^^^


Creating arrays
^^^^^^^^^^^^^^^


