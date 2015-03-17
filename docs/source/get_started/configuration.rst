.. _configuration:

Configuration
=============

.. contents::

Most of the time the default configuration of PyCLibrary should be sufficient.
However it may not always be so. Here are some ways to tweak it to your needs.

Specifying headers and libraries locations
------------------------------------------

When parsing numerous headers or using PyCLibrary in an application, it might 
prove tedious to always specifies the full path to headers files (the same can
apply to libraries if their not located in a standard location). PyCLibrary
allows you to add folder in which to look into for headers and libraries.

Consider a case in which you store the headers in a 'headers' folder by your 
script, and the library into a 'lib' folder :

.. code-block:: python

	import os
	from pyclibrary import add_header_locations, add_library_locations
	
	curr_dir = os.path.dirname(__file__)
	add_header_locations([os.path.join(curr_dir, 'headers')])
	add_library_locations([os.path.join(curr_dir, 'lib')])
	
	parser = CParser('my_lib_header.h')
	clib = CLibrary('my_lib.so', parser)
	
.. note::
	PyCLibrary does not explore sub-folders when looking for headers and 
	library (it might in the future).

Manual initialization
----------------------

The first time you create a CParser or CLibrary, PyCLibrary does some 
initialization based on your OS. It basically defines the standard known ctypes
and the specific modifiers supported by the compiler (things like __stdcall
for example).

You can manually initialize the CParser and the CLibrary by calling the 
initialization function found in pyclibrary and specifies your own types and
modifiers. You can also use the auto_init function to add things on top of your
OS specific stuff.
