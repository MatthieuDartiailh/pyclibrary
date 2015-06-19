# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Objects in this file can be used to model the public interface of a c
library. The Rootclass is CLibInterface, which refers to all typedef-,
macro-, variable-, function- objects contained in the library.

Usually the user of the pyclibrary is not getting into contact with these
objects. The CParser() is generating these objects automaticially from a
c header file and the backend is relying on the definitions of these
objects to now how to interact with the underlying c library.

The class hierarchy is:

* CLibInterface (a catalogue of all CLibBase objects in a library)
* CLibBase (base class of all objects in header file)
  * Macro
    * ValMacro (#define x ...)
    * FnMacro (#define x(...) ...)
  * CLibType
    * SimpleType
      * BuiltinType (int, char, double, ...)
      * CustomType (all references to custom types = typedefs, structs, ...)
    * EnumType
    * CompoundType
      * StructType
      * UnionType
      * BitFieldType
    * ComposedType
      * PointerType
      * ArrayType
      * FunctionType
"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
import collections
import itertools
import re
from future.moves.itertools import zip_longest
from .errors import UnknownCustomTypeError


def _lpadded_str(text):
    """An internal helper, returns '' if text is None otherwise ' '+text"""
    if text is None:
        return ''
    else:
        return ' ' + text


class CLibBase(object):

    __slots__ = ()

    def _getattrnames(self):
        """Internal method that lists all fields
        :rtype: list[str]
        """
        for cls in type(self).__mro__:
            if hasattr(cls, '__slots__'):
                for name in cls.__slots__:
                    yield name

    def copy(self):
        """Creates a shallow copy o this type.
        :rtype: CLibBase
        """
        attrs = {anm: getattr(self, anm) for anm in self._getattrnames()}
        return type(self)(**attrs)

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        return all(getattr(self, name) == getattr(other, name)
                   for cls in type(self).__mro__
                   for name in getattr(cls, '__slots__', ()))

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        code_obj = self.__init__.__code__
        init_params = code_obj.co_varnames[1:code_obj.co_argcount]
        default_vals = dict(zip(reversed(init_params),
                                reversed(self.__init__.__defaults__ or [])))

        def par_repr(param_name):
            val = getattr(self, param_name)
            if param_name not in default_vals:
                yield repr(val)
            else:
                default_val = ([] if param_name == "quals"
                               else default_vals[param_name])
                if val != default_val:
                    yield param_name + '=' + repr(val)

        return (type(self).__name__ + '(' +
                ', '.join(itertools.chain(*map(par_repr, init_params))) + ')')


class CLibType(CLibBase):
    """This is the abstract base class for all objects that are modeling a
    "C" type.
    """

    __slots__ = ('quals',)

    def __init__(self, quals=None):
        """
        :param list[str]|None quals: a list of type qualifiers
            attached to this type.
        """
        self.quals = quals or []

    def with_quals(self, add_quals):
        """
        returns this type with additional type qualifiers.

        ATTENTION: Does not modify the current type, but creates a new one,
            if necessary

        :param list[str] quals: list of type qualifiers, that shall be added
            to the current list of type qualifiers
        :rtype: CLibType
        """
        if len(add_quals) is 0:
            # qualifiers need not to be modified (optimization)
            return self
        else:
            clone = self.copy()
            clone.quals = clone.quals + add_quals
            return clone

    def resolve(self, typedefs, visited=None):
        """Resolves all references to type definitions. A reference to
        a type definition is represented by the TypeRef object. All
        CustomType objects are resolved with the help of typedefs.

        :param dict[str, CLibType] typedefs: maps the name of all known
            to the corresponding CLibType.
        :param set[str] visited: only for internal use to prevent endless
            loops on recursive typedefs
        :returns: a CLibType descendant object, that contains no TypeRef's.
        :rtype: CLibType
        """
        return self

    def c_repr(self, referrer_c_repr=None):
        """Get the c representation of this type.

        :param str|None referrer_c_repr: Has to be either the
            referrer_c_repr part of the type definition or None,
            if this is an abstract type:
            * referrer_c_repr='a' => "int *a[2]"
            * referrer_c_repr=None => "int *[2]"
        :rtype: str
        """
        raise NotImplementedError()

    def __str__(self):
        return self.c_repr()


class SimpleType(CLibType):
    """Abstract Base class for non-composed types
    (BuildinType and CustomType)
    """

    __slots__ = ('type_name',)

    def __init__(self, type_name, quals=None):
        super(SimpleType, self).__init__(quals)
        self.type_name = type_name

    def c_repr(self, referrer_c_repr=None):
        return (' '.join(self.quals + [self.type_name]) +
                _lpadded_str(referrer_c_repr))


class BuiltinType(SimpleType):
    """Is used for modeling scalar C types like:"
     * "``[signed/unsigned] char``"
     * "``[signed/unsigned] short [int]``"
     * "``[signed/unsigned] int``"
     * "``[signed/unsigned] long [int]``"
     * "``float``"
     * "``double``"
     * ...

    The class does no checks if the *type_name* is actually a valid C
    scalar type.
    """
    __slots__ = ()


class CustomType(SimpleType):
    """A reference to a custom type by name.

     These references have to follow one of the following forms:

     * "``<typedefname>``"
     * "``struct <structname>``"
     * "``union <unionname>``"
     * "``enum <enumname>``"
    """

    __slots__ = ()

    def resolve(self, typedefs, visited=None):
        visited = visited or set()
        if self.type_name in visited:
            raise UnknownCustomTypeError('{!r} is a recursive typedef'
                                         .format(self.type_name))
        else:
            visited.add(self.type_name)

        if self.type_name not in typedefs:
            raise UnknownCustomTypeError('{!r} is a unknown type'
                                         .format(self.type_name))

        resolved_type = typedefs[self.type_name].resolve(typedefs, visited)
        return resolved_type.with_quals(self.quals)


class CompoundType(CLibType):
    """Abstract base class for all types that are composed of multiple
    other types (StructType, UnionType, BitFieldType)

    The common functionality managed by this class is management of
    multiple subfields
    """

    __slots__ = ('fields',)

    KEYWORD = ''   # has to be set

    def __init__(self, fields, quals=None):
        """
        :type fields: list[tuple]
        :type quals: list[str]
        """
        super(CompoundType, self).__init__(quals)
        self.fields = fields

    def name_to_typename(self, name):
        """maps a name to the corresponding typename.
        i.e. "x -> struct x"
        """
        return self.KEYWORD + ' ' + name

    def typename_to_name(self, typename):
        """maps a typename back to the corresponding name
        i.e. struct x -> x
        """
        if not typename.startswith(self.KEYWORD + ' '):
            raise ValueError('Invalid Typename: {!r}. Has to start with {!r}'
                             .format(typename, self.KEYWORD))
        return typename[len(self.KEYWORD) + 1:]

    def _field_c_repr(self, field_tuple):
        raise NotImplementedError()

    def c_repr(self, typename=None):
        result = self.KEYWORD
        if typename:
            result += ' ' + self.typename_to_name(typename)
        result += ' {\n'

        for field in self.fields:
            result += '    ' + self._field_c_repr(field) + ';\n'

        result += '}'
        return result


class StructType(CompoundType):
    """Model of C structure type definitions."""

    __slots__ = ('packsize',)

    KEYWORD = 'struct'

    def __init__(self, fields, packsize=None, quals=None):
        """
        :param list[tuple[str, CLibType, int|None]] fields: ordered list of
            fields in this structure. Every field is represented by a tuple of
            field-name and field-type and optionally a bitsize of the field
        :param int|None packsize: if not None, the packing size of the
            structure has to be 2^n and defines the alignment of the
            members. If None, the default (=machine word size) alignment
            is used.
        :param list[str] quals: see CLibType.quals
        """
        if packsize is not None and 2**(packsize.bit_length() - 1) != packsize:
            raise ValueError('packsize has to be a value of format 2^n')
        super(StructType, self).__init__(fields, quals)
        self.packsize = packsize

    def _field_c_repr(self, field_tuple):
        field_name, field_type, field_size = field_tuple
        if field_size is None:
            return field_type.c_repr(field_name)
        else:
            return field_type.c_repr(field_name) + ' : ' + str(field_size)

    def c_repr(self, typename=None):
        if self.packsize is None:
            return super(StructType, self).c_repr(typename)
        else:
            return (
                '#pragma pack(push, {})\n'.format(self.packsize) +
                super(StructType, self).c_repr(typename) +
                '\n#pragma pack(pop)\n')


class UnionType(CompoundType):
    """Model of C union definition."""

    __slots__ = ()

    KEYWORD = 'union'

    def __init__(self, fields, quals=None):
        """
        :param list[tuple[str, CLibType]] fields: ordered list of
            fields in this structure. Every field is represented by a tuple of
            field-name and field-type
        :param list[str] quals: see CLibType.quals
        """
        super(UnionType, self).__init__(fields, quals)

    def _field_c_repr(self, field_tuple):
        field_name, field_type = field_tuple
        return field_type.c_repr(field_name)


class EnumType(CLibType):
    """Model of C enum definition."""

    __slots__ = ('values',)

    def __init__(self, values, quals=None):
        """
        :param list[tuple[str, int]] values: a list of tuples of
            value definitions (valuename -> value)
        :param list[str] quals: has to be None
        """
        if quals is not None:
            raise ValueError('enums does not support quals')
        super(EnumType, self).__init__(quals)
        self.values = values

    def c_repr(self, referrer_c_repr=None):
        if referrer_c_repr is None:
            name = ''
        elif referrer_c_repr.startswith('enum '):
            name = referrer_c_repr[len('enum '):]
        else:
            raise ValueError('{!r} requires names, starting with {!r}'
                             .format(type(self).__name__, 'enum'))
        return ''.join(
            [' '.join(self.quals + ['enum']) + _lpadded_str(name) + ' {\n'] +
            ['    {} = {},\n'.format(nm, val)
             for nm, val in self.values] +
            ['}'])


class ComposedType(CLibType):
    """Abstract base for types, that are combined with multiple
    type modifiers (PointerType, ArrayType, FunctionType).

    The common functionality managed by this class is operator precedence
    and implementation of resolve
    """

    __slots__ = ('base_type',)

    # Specify the operator precedence of this type definition operator
    # to ensure that paranthesis can be added if necessary on generating
    # the C representation of a complex type with .c_repr().
    # The higher this integer, the higher the precedence of the type
    # modifier
    PRECEDENCE = 100

    def __init__(self, base_type, quals=None):
        """
        :param CLibType base_type: base type, which is modified by this
            type modifier
        :param list[str]|None quals: see CLibType
        """
        super(ComposedType, self).__init__(quals)
        self.base_type = base_type

    def _par_c_repr(self, referrer_c_repr):
        """Internal method, that creates a parenthesized string
        of 'referrer_c_repr_plus_this' if the operator precedence
        enforces this. Only needed by .c_repr() implementations of
        ancestor classes.

        :param str referrer_c_repr: The C representation of the
            definition of the type, that refers to self (plus the
            part that is added by self)
        :returns: the complete C representation of the type
        :rtype: str
        """
        if (isinstance(self.base_type, ComposedType) and
            self.PRECEDENCE < self.base_type.PRECEDENCE):
            return self.base_type.c_repr('(' + referrer_c_repr + ')')
        else:
            return self.base_type.c_repr(referrer_c_repr)

    def resolve(self, typedefs, visited=None):
        resolved_base_type = self.base_type.resolve(typedefs, visited)
        if resolved_base_type is self.base_type:
            # this optimization avoids creation of unnecessary copies
            return self
        else:
            resolved_self = self.copy()
            resolved_self.base_type = resolved_base_type
            return resolved_self


class PointerType(ComposedType):
    """Model of C pointer definition."""

    __slots__ = ()

    PRECEDENCE = 90

    def c_repr(self, referrer_c_repr=None):
        return self._par_c_repr(' '.join(['*'] + self.quals) +
                                _lpadded_str(referrer_c_repr))


class ArrayType(ComposedType):
    """Model of C arrays definition.
    Does not only cover fixed size arrays, but also arrays of
    undefined size: ``arr[]``
    """

    __slots__ = ('size',)

    def __init__(self, base_type, size=None, quals=None):
        """
        :param CLibType base_type: type of elements in this array
        :param int|None size: size of array in elements
            (or None if size is undefined)
        :param list[str]|None quals: has to be empty!!! Is only available
            for compatibility with CLibType.copy/CLibType.eq
        """
        if quals:
            raise ValueError('arrays do not support qualifiers')
        super(ArrayType, self).__init__(base_type, quals)
        self.size = size

    def c_repr(self, referrer_c_repr=None):
        return self._par_c_repr(
            ''.join([(referrer_c_repr or ''), '[', str(self.size or ''), ']']))


class FunctionType(ComposedType):
    """Model of C function signature"""

    __slots__ = ('params',)

    def __init__(self, base_type, params=(), quals=None):
        """
        :param CLibType base_type: return value of function
        :param list[tuple[str|None, CLibType]] params: list of parameters,
            where each parameter is represented as tuple of name and type.
            If name is None, the parameter is an anonymous one.
        :param list[str]|None quals: see CLibType.quals
        """
        super(FunctionType, self).__init__(base_type, quals=quals)
        self.params = list(params)

    @property
    def return_type(self):
        """this is only a convenience property, that introduces a alias
        for .base_type, since the name "base_type" is not descriptive
        in the context of functions
        :rtype: CLibType
        """
        return self.base_type

    def c_repr(self, referrer_c_repr=None):
        if referrer_c_repr is None:
            raise ValueError('anonymous function are not allowed')
        params_str = ', '.join(ptype.c_repr(pname)
                               for pname, ptype in self.params)
        return self._par_c_repr(referrer_c_repr + '(' + params_str + ')')

    def __str__(self):
        return self.c_repr('<<funcname>>')


class Macro(CLibBase):
    """Model of C Preprocessor define"""

    __slots__ = ()

    def c_repr(self, macro_name):
        """
        returns the C code as string that corresponds to this
        C preprocessor definition

        :param str macro_name: name of macro
        :rtype: str
        """
        raise NotImplementedError()

    def __str__(self):
        return self.c_repr('<<macroname>>')


class ValMacro(Macro):
    """Model of C Preprocessor define, that is not parametrized. i.E.:
    #define X 3
    """

    __slots__ = ('content',)

    def __init__(self, content):
        """
        :param str content: the text in the define as written in
            the C source code (may contain calls to other defines)
        """
        super(ValMacro, self).__init__()
        self.content = content

    def c_repr(self, name):
        return '#define {} {}'.format(name, self.content)


class FnMacro(Macro):
    """Model of C Preprocessor define, that is parametrized. i.E.:
    #define X(a) a + 3
    """

    __slots__ = ('compiled_content', 'params')

    def _getattrnames(self):
        """hide 'compiled_content' since it is a computed value, that can
        be derived from 'content' and 'params' (see ._compile_content())
        """
        return ('content', 'params')

    def __init__(self, content, params):
        """
        :param str content: the text, that shall be inserted
            instead of the macro call. This text may contain one or
            multiple occurences of parameters from param_names
        :param list[str] params: A list of names of parameter
            needed for this macro
        """
        super(FnMacro, self).__init__()
        self.params = params
        self.compiled_content = self._compile_content(content, params)

    @staticmethod
    def _compile_content(content, params):
        """Turn a function macro spec into a string formatter, where all
        params are curly bracketed.
        """
        def parentesize_func(matchObj):
            arg_name = matchObj.group(0)
            if arg_name.startswith('"'):
                return arg_name    # this is a string -> ignore it
            else:
                return '{' + arg_name + '}'
        arg_pattern = r'("(\\"|[^"])*")|(\b({})\b)'.format('|'.join(params))
        esc_content = content.replace('{', '{{').replace('}', '}}')
        return re.sub(arg_pattern, parentesize_func, esc_content)

    @property
    def content(self):
        self_mapped_args = dict(zip(self.params, self.params))
        return self.compiled_content.format(**self_mapped_args)

    def parametrized_content(self, *args, **argv):
        """Returns the content of this function macro with replaced arguments
        """
        arg_dict = dict(zip(self.params, args))
        if set(arg_dict) & set(argv):
            raise TypeError('got multiple values for single parameter')
        arg_dict.update(argv)
        return self.compiled_content.format(**arg_dict)

    def c_repr(self, name):
        """
        returns the C code as string that corresponds to this
        C preprocessor definition

        :param str name: name of macro
        :rtype: str
        """
        return '#define {}({}) {}'.format(name, ', '.join(self.params),
                                            self.content)


class CLibInterface(collections.Mapping):
    """A complete model of the (exposed/relevant) interface of a C
    library. Corresponds to a set of header files.

    elements can either be retrieved by accessing CLibInterface as
    dictionary (and get a list of **all** objects), or by one of the
    following instance attributes, to get only objects of a specific
    class:

    :ivar dict[str, CLibType] funcs: registry of all signatures of
        exposed functions by function name
    :ivar dict[str, CLibType] vars: registry of all types of exposed
        global variables by name
    :ivar dict[str, CLibType] typedefs: registry of all types of
        typedefs/enums/structs/unions by name
    :ivar dict[str, str|None] file_map: a mapping of all names to file,
        where they are defined. If the file for a object is unknown it is
        None.
    """

    def __init__(self):
        self.funcs = dict()
        self.vars = dict()
        self.typedefs = dict()
        self.macros = dict()
        self.enums = dict()
        self.obj_maps = {
            'funcs': self.funcs,
            'vars': self.vars,
            'typedefs': self.typedefs,
            'macros': self.macros,
            'enums': self.enums
        }

        self.file_map = dict()

    def include(self, from_clib_intf):
        """
        merges another clib_intf values into this one (overwriting values,
        that are already defined in self

        :param CLibInterface from_clib_intf: clib interface to merge from
        """
        self.funcs.update(from_clib_intf.funcs)
        self.vars.update(from_clib_intf.vars)
        self.typedefs.update(from_clib_intf.typedefs)
        self.enums.update(from_clib_intf.enums)
        self.macros.update(from_clib_intf.macros)
        self.file_map.update(from_clib_intf.file_map)

    def __getitem__(self, name):
        for cls in self.obj_maps.values():
            if name in cls:
                return cls[name]
        else:
            raise KeyError("")

    def __iter__(self):
        return iter(self.file_map)

    def __len__(self):
        return len(self.file_map)

    def _add_obj(self, obj_map, name, obj, filename):
        """
        internal method for adding sth. to CLibInterface.

        :param dict[str, CLibBase] obj_map: map, into which add 'obj'
        :param str name: Name under which 'obj' shall be added
        :param CLibBase obj: object to add
        :param str filename: filename, where the obj is located in (if known)
        """
        obj_map[name] = obj
        self.file_map[name] = filename

    def add_func(self, name, func, filename=None):
        """
        official interface to add a function to CLibInterface.

        :param str name: Name of function
        :param FunctionType func: signature object of function
        :param str filename: filename, where the function is located in
            (if known)
        """
        self._add_obj(self.funcs, name, func, filename)

    def add_var(self, name, var, filename=None):
        """
        official interface to add a global variable (of any type, even
        function pointers) to CLibInterface.

        :param str name: Name of variable
        :param CLibType var: model object of variable
        :param str filename: filename, where the var is located in
            (if known)
        """
        self._add_obj(self.vars, name, var, filename)

    def add_typedef(self, name, typedef, filename=None):
        """
        official interface to add a typedef to CLibInterface.

        :param str name: Name of typedef
        :param CLibType typedef: model object of typedef
        :param str filename: filename, where the typedef is located in
            (if known)
        """
        self._add_obj(self.typedefs, name, typedef, filename)

        if isinstance(typedef, EnumType):
            for name, val in typedef.values:
                self._add_obj(self.enums, name, val, filename)

    def add_macro(self, name, macro, filename=None):
        """
        official interface to add a macro (descendant of Macro class)
        to CLibInterface.

        :param str name: Name of macro
        :param Macro macro: model object of macro
        :param str filename: filename, where the macro definition is
            located in (if known)
        """
        self._add_obj(self.macros, name, macro, filename)

    def del_macro(self, name):
        """
        remove a macro definition from the CLibInterface. Usually needed
        by #undef

        :param str name: Name of macro to remove
        """
        del self.macros[name]

    def print_all(self, filename=None):
        """Print everything stored in the CLibInterface

        Parameters
        ----------
        filename : unicode, optional
            Name of the file whose definition should be printed. If None,
            all files are printed
        """
        for obj_cls, obj_dict in sorted(self.obj_maps.items()):
            print("============== {} ==================".format(obj_cls))
            for name, obj in obj_dict.items():
                if filename is None or self.file_map[name] == filename:
                    print(obj.c_repr(name))
            print()
