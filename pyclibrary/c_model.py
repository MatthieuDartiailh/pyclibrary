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
      * CustomType (all references to custom types = typedefs or named
                    AlgebraicDataTypes)
    * AlgebraicDataType
      * EnumType
      * CompoundType
        * StructType
        * UnionType
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
from past.builtins import basestring
from .errors import UnknownCustomTypeError


def _lpadded_str(text):
    """An internal helper, returns '' if text is None otherwise ' '+text"""
    if text is None:
        return ''
    else:
        return ' ' + text


class CLibBase(object):
    """Base class for all objects managed by CLibInterface.
    It primarly provides basic python funtionality like comparing, copying
    and displaying for all derived classes.

    To make this generic approach working all derived classes have to follow
    the following conventions:
    * __slots__ has to be defined, where all attributes added by a derived
      class are inserted into. This is for optimization purposes and allows
      CLibBase to find out the attributes used by the class which is important
      for compare/copy/repr. If more/less attributes should be involved
      in CLibBase operations _getattrnames() has to be overwritten
    * The derived classes __init__ has to provide **all** attributes of
      the class (including attributes from the parent class) as parameters
      with the same name as the attributes.

    """

    __slots__ = ()

    def _getattrnames(self):
        """Internal method that lists all fields

        Returns
        -------
        list[str]
            A list of attribute names

        """
        for cls in type(self).__mro__:
            if hasattr(cls, '__slots__'):
                for name in cls.__slots__:
                    yield name

    def copy(self):
        """Creates a shallow copy of this type.

        Returns
        -------
        CLibBase
            A copy of self

        """
        attrs = {anm: getattr(self, anm) for anm in self._getattrnames()}
        return type(self)(**attrs)

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        return all(getattr(self, anm) == getattr(other, anm)
                   for anm in self._getattrnames())

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

    Parameters
    ----------
    quals : list[str], optional
        see Attributes

    Attributes
    ----------
    quals : list[str]
        A list of type qualifiers attached to this type.

    """

    __slots__ = ('quals',)

    def __init__(self, quals=None):
        self.quals = quals or []

    def with_quals(self, add_quals):
        """Add type qualifiers to this C Type.

        Does not modify the current type, but creates a new one, if necessary.

        Parameters
        ----------
        quals : list[str]
            List of type qualifiers, that shall be added to the current list
            of type qualifiers.

        Returns
        -------
        new_type : CLibType
            New type with added qualifiers.

        """
        if len(add_quals) is 0:
            # qualifiers need not to be modified => do not copy (optimization)
            return self
        else:
            clone = self.copy()
            clone.quals = clone.quals + add_quals
            return clone

    def resolve(self, typedefs, visited=None):
        """Resolves all references to type definitions.

        A reference to a type definition is represented by the TypeRef
        object. All CustomType objects are resolved with the help of typedefs.

        Parameters
        ----------
        typedefs : dict[str, CLibType]
            Maps the name of all known to the corresponding CLibType.
        visited : set[str]
            Only for internal use to prevent endless loops on recursive
            typedefs

        Returns
        -------
        CLibType
            a CLibType descendant object, that contains no TypeRef's.

        """
        return self

    def c_repr(self, referrer_c_repr=None):
        """Get the c representation of this type.

        Parameters
        ----------
        referrer_c_repr : str, optional
            Has to be either the referrer_c_repr part of the type definition
            or None, if this is an abstract type:
            * referrer_c_repr='a' => "int *a[2]"
            * referrer_c_repr=None => "int *[2]"

        Returns
        -------
        repr : str
            Formatted representation of the type.

        """
        raise NotImplementedError()

    def __str__(self):
        return self.c_repr()

    def __iter__(self):
        """Iterate through all CLibType objects, this object is build from.

        """
        return iter([])


class SimpleType(CLibType):
    """Abstract Base class for non-composed types (BuiltinType and CustomType).

    Parameters
    ----------
    type_name : str
        Name of the C type

    quals : list[str], optional
        A list of type qualifiers attached to this type.

    Attributes
    ----------
    type_name : str
        Name of C type

    """

    __slots__ = ('type_name',)

    def __init__(self, type_name, quals=None):
        super(SimpleType, self).__init__(quals)
        self.type_name = type_name

    def c_repr(self, referrer_c_repr=None):
        return (' '.join(self.quals + [self.type_name]) +
                _lpadded_str(referrer_c_repr))


class BuiltinType(SimpleType):
    """Is used for modeling scalar C types like:
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


class AlgebraicDataType(CLibType):
    """Abstract base class for algebraic type definition
    (enums, structs, union).

    """

    __slots__ = ()

    KEYWORD = ''   # has to be set

    def name_to_typename(self, name):
        """Maps a name to the corresponding typename. i.e. "x -> struct x"

        """
        return self.KEYWORD + ' ' + name

    def typename_to_name(self, typename):
        """Maps a typename back to the corresponding name  i.e. struct x -> x

        """
        if not typename.startswith(self.KEYWORD + ' '):
            raise ValueError('Invalid Typename: {!r}. Has to start with {!r}'
                             .format(typename, self.KEYWORD))
        return typename[len(self.KEYWORD) + 1:]

    def _iter_sub_c_repr(self):
        """Internal, abstract method, that returns iterator over all lines
        within brackets of an algebraic data type.

        Is called by c_repr()/named_c_repr().

        Returns
        -------
        iter[str]
            C source code lines (with trailing ';'/',')

        """
        raise NotImplementedError()

    def named_c_repr(self, typename=None, referrer_c_repr=None):
        """Returns the C representation of an algebraic data type including.

        In contrary to c_repr() this method allows to set a typename for the
        data type.

        Parameters
        ----------
        typename : str, optional
            The name of the algebraic data type. If omitted the resulting
            string is a anonymous algebraic data type.
        referrer_c_repr : str, optional
            The name of the algebraic data object. If omitted, this is only
            a type declaration, but no instantioation.

        Returns
        -------
        named_repr : str
            C code, that represents this type

        """
        result = self.KEYWORD + ' '
        if typename is not None:
            result += self.typename_to_name(typename) + ' '
        result += '{\n'

        for sub_c_repr in self._iter_sub_c_repr():
            for sub_line in sub_c_repr.split('\n'):
                result += '    ' + sub_line + '\n'

        result += '}'
        if referrer_c_repr is not None:
            result += ' ' + referrer_c_repr

        return result

    def c_repr(self, referrer_c_repr=None):
        return self.named_c_repr(referrer_c_repr=referrer_c_repr)


class CompoundType(AlgebraicDataType):
    """Abstract base class for structs and unions.

    The common functionality managed by this class is management of
    multiple subfields (see 'fields')

    Parameters
    ----------
    fields : list[tuple[str|None, CLibType]]
        see Attributes

    quals : list[str], optional
        A list of type qualifiers attached to this type.

    Attributes
    ----------
    fields : list[tuple[str|None, CLibType]]
        list of field names/field types, this union/struct is composed of.
        The name has to be set to None, if a substruct/-union's elements
        shall be visible at the parent ones level
        (i.e. "struct a { struct b; } ;")

    """

    __slots__ = ('fields',)

    KEYWORD = ''   # has to be set

    def __init__(self, fields, quals=None):
        super(CompoundType, self).__init__(quals)
        self.fields = fields

    def __iter__(self):
        for field in self.fields:
            yield field[1]


class StructType(CompoundType):
    """Model of C structure type definitions.

    Parameters
    ----------
    fields : list[tuple[str|None, CLibType]]
        see Attributes

    packsize : int, optional
        Size of packing of structure (see pack() pragma of MSVC). Has to be
        2**x.

    quals : list[str], optional
        A list of type qualifiers attached to this type.

    Attributes
    ----------
    packsize : int
        Size of packing of structure (see pack() pragma of MSVC). Has to be
        2**x.

    """

    __slots__ = ('packsize',)

    KEYWORD = 'struct'

    def __init__(self, fields, packsize=None, quals=None):
        if packsize is not None and 2**(packsize.bit_length() - 1) != packsize:
            raise ValueError('packsize has to be a value of format 2^n')
        super(StructType, self).__init__(fields, quals)
        self.packsize = packsize

    def _iter_sub_c_repr(self):
        if self.packsize is not None:
            yield '#pragma pack(push, {})'.format(self.packsize)

        for field_name, field_type, field_size in self.fields:
            if field_size is None:
                yield field_type.c_repr(field_name) + ';'
            else:
                yield '{} : {};'.format(field_type.c_repr(field_name),
                                        field_size)

        if self.packsize is not None:
            yield '#pragma pack(pop)'.format(self.packsize)


class UnionType(CompoundType):
    """Model of C union definition.

    """

    __slots__ = ()

    KEYWORD = 'union'

    def _iter_sub_c_repr(self):
        for field_name, field_type in self.fields:
            yield field_type.c_repr(field_name) + ';'


class EnumType(AlgebraicDataType):
    """Model of C enum definition.

    Parameters
    ----------
    values : list[tuple[str, int]]
        See values Attribute

    quals : list[str]
        Has to be None
        (only for interface compatibility with AlgebraicDataType)

    Attributes
    ----------
    values : list[tuple[str, int]]
        A list of tuples of value definitions (valuename -> value)

    """

    __slots__ = ('values',)

    KEYWORD = 'enum'

    def __init__(self, values, quals=None):
        super(EnumType, self).__init__(quals)
        self.values = values

    def _iter_sub_c_repr(self):
        return map('{0[0]} = {0[1]},'.format, self.values)


class ComposedType(CLibType):
    """Abstract base for types, that are combined with multiple
    type modifiers (PointerType, ArrayType, FunctionType).

    The common functionality managed by this class is operator precedence
    and implementation of resolve

    Parameters
    ----------
    base_type : CLibType
        Base type, which is modified by this type modifier.

    quals : list[str], optional
        A list of type qualifiers attached to this type.

    Attributes
    ----------
    base_type : CLibType
        The C Type object, this C type is composed of
        (i.e. pointer of base-type)

    """

    __slots__ = ('base_type',)

    # Specify the operator precedence of this type definition operator
    # to ensure that paranthesis can be added if necessary on generating
    # the C representation of a complex type with .c_repr().
    # The higher this integer, the higher the precedence of the type
    # modifier
    PRECEDENCE = 100

    def __init__(self, base_type, quals=None):
        super(ComposedType, self).__init__(quals)
        self.base_type = base_type

    def _par_c_repr(self, referrer_c_repr):
        """Internal method, that creates a parenthesized string
        of 'referrer_c_repr_plus_this' if the operator precedence
        enforces this. Only needed by .c_repr() implementations of
        ancestor classes.

        Parameters
        ----------
        referrer_c_repr str
            The C representation of the definition of the type, that refers
            to self (plus the part that is added by self)

        Returns
        -------
        str
            The complete C representation of the type.

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

    def __iter__(self):
        yield self.base_type


class PointerType(ComposedType):
    """Model of C pointer definition.

    """

    __slots__ = ()

    PRECEDENCE = 90

    def c_repr(self, referrer_c_repr=None):
        return self._par_c_repr(' '.join(['*'] + self.quals) +
                                _lpadded_str(referrer_c_repr))


class ArrayType(ComposedType):
    """Model of C arrays definition.

    Does not only cover fixed size arrays, but also arrays of
    undefined size: ``arr[]``

    Parameters
    ----------
    base_type : CLibType
        see base_type Attribute.

    size : int|None
        see base type Attributes

    quals : list[str], optional
        has to be empty!!! Is only available
        for compatibility with CLibType.copy/CLibType.eq

    Attributes
    ----------
    size : int|None
        Size of C array in count of 'base_type' elements.
        If None, the size of the array is undefined (i.e. "x[]").

    """

    __slots__ = ('size',)

    def __init__(self, base_type, size=None, quals=None):
        if quals:
            raise ValueError('arrays do not support qualifiers')
        super(ArrayType, self).__init__(base_type, quals)
        self.size = size

    def c_repr(self, referrer_c_repr=None):
        return self._par_c_repr(
            ''.join([(referrer_c_repr or ''), '[', str(self.size or ''), ']']))


class FunctionType(ComposedType):
    """Model of C function signature.

    Parameters
    ----------
    base_type : CLibType
        Return value of function.

    params : list[tuples[str|None, CLibType]
        see Attributes

    quals : list[str], optional
        A list of type qualifiers attached to this type.

    Attributes
    ----------
    params : list[tuples[str|None, CLibType]
        List of parameters, where each parameter is represented as tuple
        of name and type. If name is None, the parameter is an anonymous one
        (i.e. "void x(int);").

    """

    __slots__ = ('params',)

    def __init__(self, base_type, params=(), quals=None):
        super(FunctionType, self).__init__(base_type, quals=quals)
        self.params = list(params)

    @property
    def return_type(self):
        """This is only a convenience property, that introduces a alias
        for .base_type, since the name "base_type" is not descriptive
        in the context of functions

        Returns
        -------
        rtype : CLibType
            Function return type.

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

    def __iter__(self):
        yield self.base_type
        for pname, ptype in self.params:
            yield ptype


class Macro(CLibBase):
    """Model of C Preprocessor define."""

    __slots__ = ()

    def c_repr(self, macro_name):
        """Returns the C code as string that corresponds to this
        C preprocessor definition

        Parameters
        ----------
        macro_name : str
            Name of macro.

        Returns
        -------
        repr : str
            String representation of the macro.

        """
        raise NotImplementedError()

    def __str__(self):
        return self.c_repr('<<macroname>>')


class ValMacro(Macro):
    """Model of C Preprocessor define, that is not parametrized. i.E.:
    #define X 3

    Parameters
    ----------
    content : str
        See attributes.

    Attributes
    ----------
    content : str
        The text in the define as written in the C source code
        (may contain calls to other defines)-

    """

    __slots__ = ('content',)

    def __init__(self, content):
        super(ValMacro, self).__init__()
        self.content = content

    def c_repr(self, name):
        return '#define {} {}'.format(name, self.content)


class FnMacro(Macro):
    """Model of C Preprocessor define, that is parametrized. i.E.:
    #define X(a) a + 3

    Parameters
    ----------
    content : str
        See attributes.

    params : list[str]
        see attributes

    Attributes
    ----------
    compiled_content : str
        a formatter string, that corresponds to content, but can be used as
        formatter template, where a dictionary of parameter names (see params)
        has to be passed to get the macro output when providing the
        corresponding parameters.

    params : list[str]
        A list of parameter names, that will be replaced in content when
        applying the macro.

    """

    __slots__ = ('compiled_content', 'params')

    def _getattrnames(self):
        """Hide 'compiled_content' since it is a computed value, that can
        be derived from 'content' and 'params' (see ._compile_content())

        """
        return ('content', 'params')

    def __init__(self, content, params):
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
        return '#define {}({}) {}'.format(name, ', '.join(self.params),
                                          self.content)


class CLibInterface(collections.Mapping):
    """A complete model of the (exposed/relevant) interface of a C
    library. Corresponds to a set of header files.

    Elements can either be retrieved by accessing CLibInterface as
    dictionary (and get a list of **all** objects), or by one of the
    following instance attributes, to get only objects of a specific
    class:

    Attributes
    ----------
    funcs : dict[str, CLibType]
        A registry of all signatures of exposed functions by function name

    vars : dict[str, CLibType]
        A registry of all types of exposed global variables by name

    typedefs : dict[str, CLibType]
        A registry of all types of typedefs/enums/structs/unions by name

    macros : dict[str, Macro]
        A registry of all macros (no matter if ValMacro or FnMacro) by name

    enum : dict[str, int]
        A registry of all enum value definitions

    file_map : dict[str, str|None]
        A mapping of all names to file, where they are defined.
        If the file for a object is unknown it is None.
    storage_classes : dict[str, list[str]]
        A list of storage classes assigned to each function / global var.


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
        self.storage_classes = dict()

    def include(self, from_clib_intf):
        """Merges another clib_intf values into this one (overwriting values,
        that are already defined in self

        Parameters
        ----------
        from_clib_intf : CLibInterface
            Clib interface to merge from.

        """
        self.funcs.update(from_clib_intf.funcs)
        self.vars.update(from_clib_intf.vars)
        self.typedefs.update(from_clib_intf.typedefs)
        self.enums.update(from_clib_intf.enums)
        self.macros.update(from_clib_intf.macros)
        self.file_map.update(from_clib_intf.file_map)
        self.storage_classes.update(from_clib_intf.storage_classes)

    def __getitem__(self, name):
        for clibobj_dict in self.obj_maps.values():
            if name in clibobj_dict:
                return clibobj_dict[name]
        else:
            raise KeyError("")

    def __iter__(self):
        return iter(self.file_map)

    def __len__(self):
        return len(self.file_map)

    def _add_obj(self, obj_map, name, obj, filename):
        """Internal method for adding sth. to CLibInterface.

        Parameters
        ----------
        obj_map : dict[str, CLibBase]
            Map, into which add 'obj' parameter
        name : str
            Name under which 'obj' shall be added.
        obj : CLibBase
            object to add to obj_map
        filename : str
            Filename, where the obj is located in (if known).

        """
        def add_enum_vals(type_):
            if isinstance(type_, EnumType):
                for name, val in type_.values:
                    self._add_obj(self.enums, name, val, filename)
            elif isinstance(type_, CLibType):
                for subtype in type_:
                    add_enum_vals(subtype)

        obj_map[name] = obj
        self.file_map[name] = filename
        add_enum_vals(obj)

    def add_func(self, name, func, filename=None, storage_classes=None):
        """Official interface to add a function to CLibInterface.

        Parameters
        ----------
        name : str
            Name of function.

        func : FunctionType
            Signature object of function.

        filename : str, optional
            Filename, where the function is located in (if known)

        storage_classes : list[str], optional
            List of storage classes assigned to this function

        """
        self._add_obj(self.funcs, name, func, filename)
        self.storage_classes[name] = storage_classes or []

    def add_var(self, name, var, filename=None, storage_classes=None):
        """Official interface to add a global variable to CLibInterface.

        Parameters
        ----------
        name : str
            Name of variable.

        var : CLibType
            Type of variable.

        filename : str, optional
            Filename, where the variable is located in (if known)

        storage_classes : list[str], optional
            List of storage classes assigned to this variable

        """
        self._add_obj(self.vars, name, var, filename)
        self.storage_classes[name] = storage_classes or []

    def add_typedef(self, name, typedef, filename=None):
        """Official interface to add a typedef/struct/union/enum to
        CLibInterface.

        Parameters
        ----------
        name : str
            Name of typedef.

        typedef : CLibType
            Type of typedef.

        filename : str, optional
            Filename, where the typedef is located in (if known)

        """
        self._add_obj(self.typedefs, name, typedef, filename)

    def add_macro(self, name, macro='', filename=None):
        """Official interface to add a macro defintion to CLibInterface.

        Parameters
        ----------
        name : str
            Name of macro.

        macro : Macro|str
            Macro object to assign to 'name'. Has to be either subclass of
            Macro (FnMacro or ValMacro) or a str, that is converted to a
            ValMacro automaticially.

        filename : str, optional
            Filename, where the macro is defined in (if known)

        """
        if isinstance(macro, basestring):
            macro = ValMacro(macro)
        self._add_obj(self.macros, name, macro, filename)

    def del_macro(self, name):
        """Remove a macro definition from the CLibInterface.

        Usually needed to implement #undef.

        Parameters
        ----------
        name : str
            Name of macro to remove.

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
                    if isinstance(obj, AlgebraicDataType):
                        print(obj.named_c_repr(name))
                    else:
                        print(obj.c_repr(name))
            print()
