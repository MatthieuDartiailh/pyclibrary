# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""
Proxy to both CHeader and ctypes, allowing automatic type conversion and
function calling based on C header definitions.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from future.utils import istext, isbytes
import logging
import sys
from inspect import cleandoc
from ctypes import *

from ..errors import DefinitionError
from ..c_library import CLibrary

logger = logging.getLogger(__name__)


def make_mess(mess):
    return cleandoc(mess).replace('\n', ' ')


class CTypesCLibrary(CLibrary):
    """The CLibrary class is intended to automate much of the work in using
    ctypes by integrating header file definitions from CParser. Ths class
    serves as a proxy to a ctypes, adding a few features:
      - allows easy access to values defined via CParser
      - automatic type conversions for function calls using CParser function
        signatures
      - creates ctype classes based on type definitions from CParser

    Initialize using a ctypes shared object and a CParser:
       headers = CParser.winDefs()
       lib = CLibrary(windll.User32, headers)

    There are 3 ways to access library elements:
        lib(type, name):
            - type can be one of 'values', 'functions', 'types', 'structs',
            'unions', or 'enums'. Returns an object matching name. For values,
            the value from the headers is returned. For functions, a callable
            object is returned that handles automatic type conversion for
            arguments and return values. For structs, types, and enums, a
            ctypes class is returned matching the type specified.

        lib.name:
            - searches in order through values, functions, types, structs,
            unions, and enums from header definitions and returns an object for
            the first match found. The object returned is the same as returned
            by lib(type, name). This is the preferred way to access elements
            from CLibrary, but may not work in some situations (for example, if
            a struct and variable share the same name).

        lib[type]:
            - Accesses the header definitions directly, returns definition
            dictionaries based on the type requested. This is equivalent to
            headers.defs[type].

    Parameters
    ----------
    lib:
        Library object.

    headers : CParser
        CParser holding all the definitions.

    prefix : unicode
        Prefix to remove from all definitions.

    fix_case : bool
        Should name be converted from camelCase to python PEP8 compliants
        names.

    """
    #: Private flag allowing to know if the class has been initiliased.
    _init = False

    #: Balise to use when a NULL pointer is needed
    Null = object()

    #: Types (filled by _init_clibrary)
    c_types = {}

    #: Types for which ctypes provides a special pointer type.
    c_ptr_types = {'char': c_char_p,
                   'wchar': c_wchar_p,
                   'void': c_void_p
                   }

    def __init__(self, lib, headers, prefix=None, fix_case=True):
        # name everything using underscores to avoid name collisions with
        # library

        self._lib_ = lib
        self._headers_ = headers
        self._defs_ = headers.defs
        if prefix is None:
            self._prefix_ = []
        elif isinstance(prefix, list):
            self._prefix_ = prefix
        else:
            self._prefix_ = [prefix]

        self._objs_ = {}
        for k in ['values', 'functions', 'types', 'structs', 'unions',
                  'enums']:
            self._objs_[k] = {}
        self._all_objs_ = {}
        self._structs_ = {}
        self._unions_ = {}

    def __call__(self, typ, name):
        if typ not in self._objs_:
            typs = self._objs_.keys()
            raise KeyError("Type must be one of {}".format(typs))

        if name not in self._objs_[typ]:
            self._objs_[typ][name] = self._make_obj_(typ, name)

        return self._objs_[typ][name]

    def _all_names_(self, name):
        return [name] + [p + name for p in self._prefix_]

    def _make_obj_(self, typ, name):
        names = self._all_names_(name)

        for n in names:
            if n in self._objs_:
                return self._objs_[n]

        for n in names:  # try with and without prefix
            if (n not in self._defs_[typ] and
                not (typ in ['structs', 'unions', 'enums'] and
                     n in self._defs_['types'])):
                continue

            if typ == 'values':
                return self._defs_[typ][n]
            elif typ == 'functions':
                return self._get_function(n)
            elif typ == 'types':
                obj = self._defs_[typ][n]
                return self._ctype(obj)
            elif typ == 'structs':
                return self._cstruct('structs', n)
            elif typ == 'unions':
                return self._cstruct('unions', n)
            elif typ == 'enums':
                # Allow automatic resolving of typedefs that alias enums
                if n not in self._defs_['enums']:
                    if n not in self._defs_['types']:
                        raise KeyError('No enums named "{}"'.format(n))
                    typ = self._headers_.eval_type([n])[0]
                    if typ[:5] != 'enum ':
                        raise KeyError('No enums named "{}"'.format(n))
                    # Look up internal name of enum
                    n = self._defs_['types'][typ][1]
                obj = self._defs_['enums'][n]

                return obj
            else:
                raise KeyError("Unknown type {}".format(typ))

        raise NameError(name)

    def __getattr__(self, name):
        """Used to retrieve any type of definition from the headers.

        Searches for the name in this order:
        values, functions, types, structs, unions, enums.

        """
        if name not in self._all_objs_:
            names = self._all_names_(name)
            for k in ['values', 'functions', 'types', 'structs', 'unions',
                      'enums', None]:
                if k is None:
                    raise NameError(name)
                obj = None
                for n in names:
                    if n in self._defs_[k]:
                        obj = self(k, n)
                        break
                if obj is not None:
                    break
            self._all_objs_[name] = obj
        return self._all_objs_[name]

    def __getitem__(self, name):
        """Used to retrieve a specific dictionary from the headers.

        """
        return self._defs_[name]

    def __repr__(self):
        return "<CLibrary instance: %s>" % str(self._lib_)

    def _get_function(self, func_name):
        try:
            func = getattr(self._lib_, func_name)
        except:
            mess = "Function name '{}' appears in headers but not in library!"
            raise KeyError(mess.format(func))

        return CFunction(self, func, self._defs_['functions'][func_name],
                         func_name)

    def _ctype(self, typ, pointers=True):
        """Return a ctype object representing the named type.

        If pointers is True, the class returned includes all pointer/array
        specs provided. Otherwise, the class returned is just the base type
        with no pointers.

        """
        try:
            typ = self._headers_.eval_type(typ)
            mods = typ[1:][:]

            # Create the initial type
            # Some types like ['char', '*'] have a specific ctype (c_char_p)
            # (but only do this if pointers == True)
            if (pointers and len(typ) > 1 and typ[1] == '*' and
                    typ[0] in self.c_ptr_types):
                cls = self.c_ptr_types[typ[0]]
                mods = typ[2:]

            # If the base type is in the list of existing ctypes:
            elif typ[0] in self.c_types:
                cls = CLibrary.c_types[typ[0]]

            # structs, unions, enums:
            elif typ[0][:7] == 'struct ':
                cls = self._cstruct('structs', self._defs_['types'][typ[0]][1])
            elif typ[0][:6] == 'union ':
                cls = self._cstruct('unions', self._defs_['types'][typ[0]][1])
            elif typ[0][:5] == 'enum ':
                cls = c_int

            # void
            elif typ[0] == 'void':
                cls = None
            else:
                raise KeyError("Can't find base type for {}".format(typ))

            if not pointers:
                return cls

            # apply pointers and arrays
            while len(mods) > 0:
                m = mods.pop(0)
                if istext(m):  # pointer or reference
                    if m[0] == '*' or m[0] == '&':
                        for i in m:
                            cls = POINTER(cls)

                elif isinstance(m, list):      # array
                    for i in m:
                        # -1 indicates an 'incomplete type' like "int
                        # variable[]"
                        if i == -1:
                            # which we should interpret like "int *variable"
                            cls = POINTER(cls)
                        else:
                            cls = cls * i

                # Probably a function pointer
                elif isinstance(m, tuple):
                    # Find pointer and calling convention
                    is_ptr = False
                    conv = '__cdecl'
                    if len(mods) == 0:
                        mess = "Function signature with no pointer:"
                        raise DefinitionError(mess, m, mods)
                    for i in [0, 1]:
                        if len(mods) < 1:
                            break
                        if mods[0] == '*':
                            mods.pop(0)
                            is_ptr = True
                        elif mods[0] in ['__stdcall', '__cdecl']:
                            conv = mods.pop(0)
                        else:
                            break
                    if not is_ptr:
                        mess = make_mess("""Not sure how to handle type
                            (function without single pointer): {}""")
                        raise DefinitionError(mess.format(typ))

                    if conv == '__stdcall':
                        mkfn = WINFUNCTYPE

                    else:
                        mkfn = CFUNCTYPE

                    args = [self._ctype(arg[1]) for arg in m]
                    cls = mkfn(cls, *args)

                else:
                    mess = "Not sure what to do with this type modifier: '{}'"
                    raise TypeError(mess.format(p))
            return cls

        except:
            logger.error("Error while processing type: {}".format(typ))
            raise

    def _cstruct(self, str_type, str_name):
        if str_name not in self._structs_:

            str_name = self._resolve_struct_alias(str_type, str_name)

            # Pull struct definition
            defn = self._defs_[str_type][str_name]

            # create ctypes class
            defs = defn['members'][:]
            if str_type == 'structs':
                class s(Structure):
                    def __repr__(self):
                        return "<ctypes struct '%s'>" % strName
            elif str_type == 'unions':
                class s(Union):
                    def __repr__(self):
                        return "<ctypes union '%s'>" % strName

            # Must register struct here to allow recursive definitions.
            self._structs_[str_name] = s

            if defn['pack'] is not None:
                s._pack_ = defn['pack']

            # Assign names to anonymous members
            members = []
            anon = []
            for i, d in enumerate(defs):
                if d[0] is None:
                    c = 0
                    while True:
                        name = 'anon_member%d' % c
                        if name not in members:
                            d[0] = name
                            anon.append(name)
                            break
                members.append(d[0])

            s._anonymous_ = anon
            s._fields_ = [(m[0], self._ctype(m[1])) for m in defs]
            s._defaults_ = [m[2] for m in defs]

        return self._structs_[strName]


class CFunction(object):
    """Wrapper object for a function from the library.

    """
    def __init__(self, lib, func, sig, name):
        self.lib = lib
        self.func = func

        # looks like [return_type, [(argName, type, default),
        #                           (argName, type, default), ...]]
        self.sig = list(sig)

        # remove void args from list
        self.sig[1] = [s for s in sig[1] if s[1] != ['void']]
        for conv in ['__stdcall', '__cdecl']:
            if conv in self.sig[0]:
                self.sig[0].remove(conv)
        self.name = name
        self.res_type = lib._ctype(self.sig[0])
        func.res_type = self.res_type
        self.arg_types = [lib._ctype(s[1]) for s in self.sig[1]]
        func.argtypes = self.arg_types
        self.req_args = [x[0] for x in self.sig[1] if x[2] is None]
        # Mapping from argument names to indices
        self.arg_inds = {s[0]: i for i, s in enumerate(self.sig[1])}

    def arg_c_type(self, arg):
        """Return the ctype required for the specified argument.

        Parameters
        ----------
        arg : int or unicode
            Name or index of the argument whose type should be returned.

        """
        if istext(arg) or isbytes(arg):
            arg = self.arg_inds[arg]
        return self.lib._ctype(self.sig[1][arg][1])

    def __call__(self, *args, **kwargs):
        """Invoke the SO or dll function referenced, converting all arguments
        to the correct type.

        Keyword arguments are allowed as long as the header specifies the
        argument names. Arguments which are passed byref may be omitted
        entirely, and will be automaticaly generated. To pass a NULL pointer,
        give None as the argument.
        Returns the return value of the function call as well as all of the
        arguments (so that objects passed by reference can be retrieved).

        """
        # We'll need at least this many arguments.
        arg_list = [None] * max(len(self.req_args), len(args))

        # First fill in args
        for i in range(len(args)):
            if args[i] is None:
                arg_list[i] = self.lib.Null
            else:
                arg_list[i] = args[i]

        # Next fill in kwargs
        for k in kwargs:
            if k not in self.arg_inds:
                print("Function signature:", self.pretty_signature())
                mess = "Function signature has no argument named '{}'"
                raise TypeError(mess.format(k))

            ind = self.arg_inds[k]
            # Stretch argument list if needed
            if ind >= len(arg_list):  #
                arg_list += [None] * (ind - len(arg_list) + 1)
            if kwargs[k] is None:
                arg_list[ind] = self.lib.Null
            else:
                arg_list[ind] = kwargs[k]

        guessed_args = []
        # Finally, fill in remaining arguments if they are pointers to
        # int/float/void*/struct values (we assume these are to be modified by
        # the function and their initial value is not important)
        for i, arg in enumerate(arg_list):
            if arg is None or arg is self.lib.Null:
                try:
                    sig = self.sig[1][i][1]
                    arg_type = self.lib._headers_.eval_type(sig)

                    # request to build a null pointer
                    if arg_list[i] is self.lib.Null:
                        if len(arg_type) < 2:
                            mess = make_mes("""Cannot create NULL for
                                non-pointer argument type: {}""")
                            raise TypeError(mess.format(arg_type))
                        arg_list[i] = self.lib._ctype(sig)()

                    else:
                        if (arg_type == ['void', '**'] or
                                arg_type == ['void', '*', '*']):
                            cls = c_void_p
                        else:
                            # Must be 2-part type, second part must be '*'
                            assert len(argType) == 2 and argType[1] == '*'
                            cls = self.lib._ctype(sig, pointers=False)
                        arg_list[i] = pointer(cls(0))
                        guessed_args.append(i)

                except:
                    if sys.exc_info()[0] is not AssertionError:
                        raise
                    print("Function signature:", self.pretty_signature())
                    mess = "Function call '{}' missing required argument {} {}"
                    raise TypeError(mess.format(self.name, i,
                                                self.sig[1][i][0]))

        try:
            res = self.func(*arg_list)
        except Exception:
            logger.error("Function call failed. Signature is: {}".format(
                self.pretty_signature()))
            logger.error("Arguments: {}".format(arg_ist))
            logger.error("Argtypes: {}".format(self.func.argtypes))
            raise

        cr = CallResult(res, arglist, self.sig, guessed=guessed_args)
        return cr

    def pretty_signature(self):
        args = (''.join(self.sig[0]), self.name,
                ', '.join(["{} {}".format("".join(map(s[1])), s[0])
                          for s in self.sig[1]])
                )
        return "{} {}({})".format(args)


class CallResult:
    """Class for bundling results from C function calls.

    Allows access to the function  value as well as all of the arguments, since
    the function call will often return extra values via these arguments.
      - Original ctype objects can be accessed via result.rval or result.args
      - Python values carried by these objects can be accessed using ()
    To access values:
       - The return value: ()
       - The nth argument passed: [n]
       - The argument by name: ['name']
       - All values that were auto-generated: .auto()

    The class can also be used as an iterator, so that tuple unpacking is
    possible:
       ret, arg1, arg2 = lib.run_some_function(...)

    """
    def __init__(self, rval, args, sig, guessed):
        self.rval = rval        # return value of function call
        self.args = args        # list of arguments to function call
        self.sig = sig          # function signature
        self.guessed = guessed  # list of arguments that were auto-generated

    def __call__(self):
        if self.sig[0] == ['void']:
            return None
        return self.make_val(self.rval)

    def __getitem__(self, n):
        if isinstance(n, int):
            return self.make_val(self.args[n])
        elif istext(n) or isbytes(n):
            ind = self.find_arg(n)
            return self.make_val(self.args[ind])
        else:
            raise ValueError("Index must be int or str.")

    def __setitem__(self, n, val):
        if type(n) is int:
            self.args[n] = val
        elif type(n) is str:
            ind = self.find_arg(n)
            self.args[ind] = val
        else:
            raise ValueError("Index must be int or str.")

    def make_val(self, obj):
        while not hasattr(obj, 'value'):
            if not hasattr(obj, 'contents'):
                return obj
            try:
                obj = obj.contents
            except ValueError:
                return None

        return obj.value

    def find_arg(self, arg):
        for i, a in enumerate(self.sig[1]):
            if a[0] == arg:
                return i
        mess = make_mess("""Can't find argument '{}' in function signature.
                         Arguments are: {}""")
        raise KeyError(mess.format(arg, str([a[0] for a in self.sig[1]])))

    def __iter__(self):
        yield self()
        for i in range(len(self.args)):
            yield(self[i])

    def auto(self):
        return [self[n] for n in self.guessed]


def _init_clibrary(extra_types={}):
    # First load all standard types
    CLibrary.cTypes = {
        'char': c_char,
        'wchar': c_wchar,
        'unsigned char': c_ubyte,
        'short': c_short,
        'short int': c_short,
        'unsigned short': c_ushort,
        'unsigned short int': c_ushort,
        'int': c_int,
        'unsigned': c_uint,
        'unsigned int': c_uint,
        'long': c_long,
        'long int': c_long,
        'unsigned long': c_ulong,
        'unsigned long int': c_ulong,
        'long long': c_longlong,
        'long long int': c_longlong,
        'unsigned __int64': c_ulonglong,
        'unsigned long long': c_ulonglong,
        'unsigned long long int': c_ulonglong,
        'float': c_float,
        'double': c_double,
        'long double': c_longdouble,
        'uint8_t': c_uint8,
        'int8_t': c_int8,
        'uint16_t': c_uint16,
        'int16_t': c_int16,
        'uint32_t': c_uint32,
        'int32_t': c_int32,
        'uint64_t': c_uint64,
        'int64_t': c_int64
    }

    # Now complete the list with some more exotic types
    CLibrary.cTypes.update(extra_types)
    CLibrary._init = True
