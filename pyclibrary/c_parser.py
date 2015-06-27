# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""
Used for extracting data such as macro definitions, variables, typedefs, and
function signatures from C header files.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

import sys
import re
import os
import logging
from inspect import cleandoc
from future.utils import istext, isbytes
from past.builtins import basestring
from ast import literal_eval
from traceback import format_exc
import pickle

from .errors import DefinitionError, InvalidCacheError
from pyclibrary import c_model

# Import parsing elements
from .thirdparty.pyparsing import \
    (ParserElement, ParseResults, Forward, Optional, Word, WordStart,
     WordEnd, Keyword, Regex, Literal, SkipTo, ZeroOrMore, OneOrMore,
     Group, LineEnd, stringStart, quotedString, oneOf, nestedExpr,
     delimitedList, restOfLine, cStyleComment, alphas, alphanums, hexnums,
     lineno, Suppress, NoMatch, ParseException)
ParserElement.enablePackrat()

logger = logging.getLogger(__name__)

__all__ = ['win_defs', 'CParser', 'MSVCParser', 'SYS_HEADER_DIRS']

if sys.platform == 'darwin':
    SYS_HEADER_DIRS = ('/usr/local/include', '/usr/include',
                       '/System/Library/Frameworks', '/Library/Frameworks')
elif sys.platform == 'linux2':
    SYS_HEADER_DIRS = ('/usr/local/include', '/usr/target/include',
                       '/usr/include')
else:
    SYS_HEADER_DIRS = ()


def win_defs_parser(version=1500, force_update=False, sdk_dir=None):
    """Creates a parser, that is prepared with windows header files.

    These definitions can be used before parsing another file like this:
    >>> win_parser = win_defs_parser()
    >>> win_parser.read("headerFile.h")

    Definitions are pulled from a selection of header files included in Visual
    Studio (possibly not legal to distribute? Who knows.), some of which have
    been abridged because they take so long to parse.

    Parameters
    ----------
    version : unicode
        Version of the MSVC to consider when parsing.

    force_update : bool, optional
        If True, the cached header files are reparsed, even if they are
        up-to-date

    sdk_dir : str
        Has to refer to the visual studio header files directory, where
        all windows header files are located in.

    Returns
    -------
    parser : MSVCParser
        CParser containing all the infos from te windows headers.

    """
    if sdk_dir is None:
        sdk_dir = []
    dir = os.path.dirname(__file__)
    cache_file_name = os.path.join(dir, 'headers', 'WinDefs.cache')

    parser = MSVCParser(header_dirs=[sdk_dir],
                        predef_macros={'_WIN32': '', 'NO_STRICT': ''},
                        msc_ver=version, arch=32, )

    # the fix header file order is very fragile, as there is no clean
    # dependency tree between them. This is why the 'DECLARE_HANDLE' has to be
    # provided (DECLARE_HANDLE is defined in WinNt.h, but used in WinDef.h,
    # although WinNt.h uses a lot of defines from WinDef.h. By manually
    # defining DECLARE_HANDLE WinDef.h can be parsed before WinNt.h and
    # WinNt.h can then use all definitions from WinDef.h when being parsed)
    parser.clib_intf.add_macro(
        'DECLARE_HANDLE', c_model.FnMacro('typedef HANDLE name', ['name']))

    if not force_update:
        try:
            parser.load_cache(cache_file_name, check_validity=True)
        except InvalidCacheError:
            pass
        else:
            logger.debug("Loaded cached definitions; will skip parsing.")
            # Cached values loaded successfully, nothing left to do here
            return parser

    header_files = ['specstrings.h', 'specstrings_strict.h', 'Rpcsal.h',
                    'WinDef.h', 'BaseTsd.h', 'WTypes.h',
                    'WinNt.h', 'WinBase.h', 'WinUser.h']
    for header_file in header_files:
        parser.read(header_file)

    logger.debug("Writing cache file '{}'".format(cache_file_name))
    parser.write_cache(cache_file_name)
    return parser


class CParser(object):
    """A Parser object is used to analyse a C header file and store its
      declarations in a corresponding CLibInterface. Every Parser generates
      an assigned CLibInterface on creation. Then as many header files as
      needed can be added to this CLibInterface by calling CParser.read() per
      header file.

      Alternatively the it is also possible to call the basic operations
      .remove_comment(), .preprocess(), .parse() individially.

      For getting better performance the result of a/multiple read() can be
      stored with CParser.write_cache() once and then restored via
      CParser.load_cache() for getting better performance.

    Parameters
    ----------
    header_dirs : list[str], optional
        A list of directory names, that shall be used to search relative
        header file names in. If absolute header file names are provided to
        .read() this is ignored

    predef_macros : list[tuple[str, str]], optional
        A optional list of predefined macros

    Attributes
    ----------
    clib_intf : CLibInterface
        All parse results are stored here. To detach this object from the
        parser call .reset_clib_intf().

    Example
    -------
    Create parser object:

    >>> p = CParser()

    Remove comments, preprocess, and search for declarations

    >>> p.read('header_file1.h')
    >>> p.read('header_file2.h')

    Just to see what was successfully parsed from the files

    >>> p.clib_intf.print_all()

    Access parsed declarations

    >>> p.clib_intf['var1']

    """
    #: Increment every time cache structure or parsing changes to invalidate
    #: old cache files.
    cache_version = 3

    def __init__(self, header_dirs=None, predef_macros=None):
        self._build_parser()

        self.predef_macros = {
            # dummy values for predefined macros
            '__DATE__': 'Jan 01 1970',
            '__FILE__': 'filename.h',
            '__LINE__': '1',
            '__STDC__': '1',
            '__TIME__': '00:00:00',
            '__TIMESTAMP__': 'Jan 01 1970 00:00:00'}
        if predef_macros:
            self.predef_macros.update(predef_macros)
        self.reset_clib_intf()

        self.header_dirs = header_dirs or []

        # these attributes are needed only temporarly, while parsing a file
        self.cur_pack_list = None
        self.cur_file_name = None


    def read(self, hdr_file, replace_texts=None, virtual_filename=None,
             preproc_out_file=None):
        """ Remove comments, preprocess, and parse declarations from all
        files.

        This operates in memory, and thus does not alter the original files.

        Parameters
        ----------
        hdr_file : str|file-like-obj
            The fileobj (or filename) of the header source code.

        replace_texts : dict[str, str], optional
            Mapping of regular expressions to replace texts. Is used if the
            source code contains constructs, that cannot be processed by
            pyclibrary.

        virtual_filename : str, optional
            if hdr_file is a file-like object this allows to provide a
            filename. Alternatively the real filename provided in hdr_file can
            be replaced by a 'virtual' filename

        preproc_out_file : file-like-obj, optional
            If a file is specified, the output of the preprocessor is written
            to this file. For debugging purposes set:
            preproc_out_file=sys.stdout

        """
        if isinstance(hdr_file, basestring):
            filename = self.find_header(hdr_file)
            hdr_file = open(filename, 'rU')
        else:
            filename = getattr(hdr_file, 'name', None)
        
        try:
            self.cur_file_name = virtual_filename or filename
            
            srccode = hdr_file.read()
            fixed_srccode = self.fix_bad_code(srccode, replace_texts)
            logger.debug(cleandoc('Parsing C header files (no valid cache '
                                  'found). This could take several minutes.'))
    
            logger.debug("Removing comments from file '{}'..."
                         .format(self.cur_file_name))
            nocomments_srccode = self.remove_comments(fixed_srccode)

            logger.debug("Preprocessing file '{}'..."
                         .format(self.cur_file_name))
            pack_list = []
            preproc_srccode = self.preprocess(nocomments_srccode, pack_list)
            if preproc_out_file is not None:
                preproc_out_file.write(preproc_srccode)

            logger.debug("Parsing definitions in file '{}'..."
                         .format(self.cur_file_name))

            self.parse(preproc_srccode, pack_list)
            self.file_order.append(self.cur_file_name)

        finally:
            self.cur_file_name = None

    def reset_clib_intf(self):
        """Detaches the current .clib_intf object from the parser and creates
        a new one.

        Returns
        -------
        CLibInterface
            the backend for further .read() operations. Will be filled with
            predefined macros.

        """
        self.clib_intf = c_model.CLibInterface()
        for name, content in self.predef_macros.items():
            self.clib_intf.add_macro(name, content)
        self.file_order = []

    def load_cache(self, cache_file, check_validity=False):
        """Load a cache file.

        Used internally if cache is specified in process_all().

        Parameters
        ----------
        cache_file : unicode
            Path of the file from which the cache should be loaded.

        check_validity : bool, optional
            If True, then run several checks before loading the cache:
              - cache file must not be older than any source files
              - cache file must not be older than this library file
              - options recorded in cache must match options used to initialize
              CParser

        Returns
        -------
        result : CLibInterface
            cache lib interface read from interface.

        """
        # Make sure cache file exists
        if not istext(cache_file):
            raise ValueError("Cache file option must be a unicode.")
        if not os.path.isfile(cache_file):
            # If file doesn't exist, search for it in this module's path
            d = os.path.dirname(__file__)
            cache_file = os.path.join(d, "headers", cache_file)
            if not os.path.isfile(cache_file):
                logger.debug("Can't find requested cache file.")
                raise InvalidCacheError("Can't find requested cache file.")

        try:
            # Read cache file
            cache = pickle.load(open(cache_file, 'rb'))
        except Exception:
            logger.exception("Warning--cache read failed:")
            raise InvalidCacheError('failed to read cache file')
        else:
            self.clib_intf = cache['clib_intf']
            self.file_order = cache['file_order']

        if check_validity:
            if cache['predef_macros'] != self.predef_macros:
                mess = "Different list of predefined macros"
                logger.debug(mess)
                raise InvalidCacheError('Predefined Macros does not match')

            # Make sure __init__ options match
            if cache['version'] < self.cache_version:
                mess = "Cache file is not valid--cache format has changed."
                logger.debug(mess)
                raise InvalidCacheError('Cache Expired')

            # Make sure cache is newer than all input files
            mtime = os.stat(cache_file).st_mtime
            for f in self.file_order:
                # If file does not exist, then it does not count against the
                # validity of the cache.
                if os.path.isfile(f) and os.stat(f).st_mtime > mtime:
                    logger.debug("Cache file is out of date.")
                    raise InvalidCacheError('Cache file is out of date.')


    def write_cache(self, cache_file):
        """Store all parsed declarations to cache. Used internally.

        """
        cache = {}
        cache['clib_intf'] = self.clib_intf
        cache['version'] = self.cache_version
        cache['file_order'] = self.file_order
        cache['predef_macros'] = self.predef_macros
        pickle.dump(cache, open(cache_file, 'wb'), protocol=2)

    def find_header(self, hdr_filename):
        """Try to find the specified headers.

        """
        if os.path.isabs(hdr_filename):
            return hdr_filename

        for dir in self.header_dirs:
            path = os.path.join(dir, hdr_filename)
            if os.path.isfile(path):
                return path
        else:
            raise IOError('cannot find header file {!r}'.format(hdr_filename))

    def fix_bad_code(self, srccode, replace=None):
        """Replaces all occurences of patterns in source code, that are not
        compatible with CParser.

        Parameters
        ----------
        srccode : str
            Text of source code.

        replace : dict, optional
            Dictionary containing strings to replace by the associated value
            when loading the file.

        """
        # U causes all newline types to be converted to \n
        if replace is not None:
            for s in replace:
                srccode = re.sub(s, replace[s], srccode)

        return srccode

    # =========================================================================
    # --- Processing functions
    # =========================================================================

    def remove_comments(self, srccode):
        """Remove all comments from file.

        Operates in memory, does not alter the original files.

        """
        cplusplus_line_comment = Literal("//") + restOfLine
        # match quoted strings first to prevent matching comments inside quotes
        comment_remover = (quotedString | cStyleComment.suppress() |
                           cplusplus_line_comment.suppress())
        return comment_remover.transformString(srccode)

    def preprocess(self, srccode, pack_list):
        """Scan named file for preprocessor directives, removing them while
        expanding macros.

        Operates in memory, does not alter the original files.

        Currently support :
        - conditionals : ifdef, ifndef, if, elif, else (defined can be used
        in a if statement).
        - definition : define, undef
        - pragmas : pragma

        """
        # Stack for #pragma pack push/pop
        assert len(pack_list) == 0
        pack_list.append((0, None))

        pack_stack = [(None, None)]
        packing = None  # Current packing value

        # First join together lines split by \\n
        joined_srccode = Literal('\\\n').suppress().transformString(srccode)

        # Define the structure of a macro definition
        name = self.generic_ident()('name')
        deli_list = Optional(self.lparen + delimitedList(name) + self.rparen)
        self.pp_define = (name.setWhitespaceChars(' \t')("macro") +
                          deli_list.setWhitespaceChars(' \t')('args') +
                          SkipTo(LineEnd())('value'))
        self.pp_define.setParseAction(self.process_macro_defn)

        macro_name_pattern = name + SkipTo(LineEnd())('rest')

        # Comb through lines, process all directives
        lines = joined_srccode.split('\n')

        result = []

        directive = re.compile(r'\s*#\s*([a-zA-Z]+)(.*)$')
        if_true = [True]
        if_hit = []
        for i, line in enumerate(lines):
            new_line = ''
            m = directive.match(line)

            # Regular code line
            if m is None:
                # Only include if we are inside the correct section of an IF
                # block
                if if_true[-1]:
                    new_line = self.expand_macros(line)

            # Macro line
            else:
                d = m.groups()[0]
                rest = m.groups()[1]

                if d == 'ifdef':
                    d = 'if'
                    rest = 'defined ' + rest
                elif d == 'ifndef':
                    d = 'if'
                    rest = '!defined ' + rest

                # Evaluate 'defined' operator before expanding macros
                if d in ['if', 'elif']:
                    def pa(t):
                        return ['0', '1'][t['name'] in self.clib_intf.macros]

                    rest = (Keyword('defined') +
                            (name | self.lparen + name + self.rparen)
                            ).setParseAction(pa).transformString(rest)

                elif d in ['define', 'undef']:
                    try:
                        match = macro_name_pattern.parseString(rest.lstrip())
                    except ParseException:
                        raise DefinitionError('invalid macro definition: {!r}'
                                              .format(line))
                    else:
                        macro_name = match.name
                        rest = match.rest

                # Expand macros if needed
                if rest is not None and (all(if_true) or d in ['if', 'elif']):
                    rest = self.expand_macros(rest)

                if d == 'elif':
                    if if_hit[-1] or not all(if_true[:-1]):
                        ev = False
                    else:
                        ev = self.eval_preprocessor_expr(rest)

                    logger.debug("  "*(len(if_true)-2) + line +
                                 '{}, {}'.format(rest, ev))

                    if_true[-1] = ev
                    if_hit[-1] = if_hit[-1] or ev

                elif d == 'else':
                    logger.debug("  "*(len(if_true)-2) + line +
                                 '{}'.format(not if_hit[-1]))
                    if_true[-1] = (not if_hit[-1]) and all(if_true[:-1])
                    if_hit[-1] = True

                elif d == 'endif':
                    if_true.pop()
                    if_hit.pop()
                    logger.debug("  "*(len(if_true)-1) + line)

                elif d == 'if':
                    if all(if_true):
                        ev = self.eval_preprocessor_expr(rest)
                    else:
                        ev = False
                    logger.debug("  "*(len(if_true)-1) + line +
                                 '{}, {}'.format(rest, ev))
                    if_true.append(ev)
                    if_hit.append(ev)

                elif d == 'define':
                    if if_true[-1]:
                        logger.debug("  "*(len(if_true)-1) + "define: " +
                                     '{}, {}'.format(macro_name, rest))
                        try:
                            # Macro is registered here
                            self.pp_define.parseString(
                                macro_name + ' ' + rest)
                        except Exception:
                            logger.exception(
                                'Error processing macro definition:{}, {}'
                                .format(macro_name, rest))

                elif d == 'undef':
                    if if_true[-1]:
                        try:
                            self.clib_intf.del_macro(macro_name.strip())
                        except Exception:
                            if sys.exc_info()[0] is not KeyError:
                                mess = "Error removing macro definition '{}'"
                                logger.exception(
                                    mess.format(macro_name.strip()))

                # Check for changes in structure packing
                # Support only for #pragme pack (with all its variants
                # save show), None is used to signal that the default packing
                # is used.
                # Those two definition disagree :
                # https://gcc.gnu.org/onlinedocs/gcc/Structure-Packing-Pragmas.html
                # http://msdn.microsoft.com/fr-fr/library/2e70t5y1.aspx
                # The current implementation follows the MSVC doc.
                elif d == 'pragma':
                    m = re.match(r'\s+pack\s*\(([^\)]*)\)', rest)
                    if if_true[-1] and m:
                        if m.groups():
                            opts = [s.strip() for s in m.groups()[0].split(',')]

                        pushpop = id = val = None
                        for o in opts:
                            if o in ['push', 'pop']:
                                pushpop = o
                            elif o.isdigit():
                                val = int(o)
                            else:
                                id = o

                        packing = val

                        if pushpop == 'push':
                            pack_stack.append((packing, id))
                        elif opts[0] == 'pop':
                            if id is None:
                                pack_stack.pop()
                            else:
                                ind = None
                                for j, s in enumerate(pack_stack):
                                    if s[1] == id:
                                        ind = j
                                        break
                                if ind is not None:
                                    pack_stack = pack_stack[:ind]
                            if val is None:
                                packing = pack_stack[-1][0]

                        mess = ">> Packing changed to {} at line {}"
                        logger.debug(mess.format(str(packing), i))
                        pack_list.append((i, packing))

                else:
                    # Ignore any other directives
                    mess = 'Ignored directive {} at line {}'
                    logger.debug(mess.format(d, i))

            result.append(new_line)

        return '\n'.join(result)

    def eval_preprocessor_expr(self, expr):
        # Make a few alterations so the expression can be eval'd
        macro_diffs = (
            Literal('!').setParseAction(lambda: ' not ') |
            Literal('&&').setParseAction(lambda: ' and ') |
            Literal('||').setParseAction(lambda: ' or ') |
            Word(alphas + '_', alphanums + '_').setParseAction(lambda: '0'))
        expr2 = macro_diffs.transformString(expr).strip()

        try:
            ev = bool(eval(expr2))
        except Exception:
            mess = "Error evaluating preprocessor expression: {} [{}]\n{}"
            logger.debug(mess.format(expr, repr(expr2), format_exc()))
            ev = False
        return ev

    def process_macro_defn(self, t):
        """Parse a #define macro and register the definition.

        """
        logger.debug("Processing MACRO: {}".format(t))
        macro_val = t.value.strip()
        if macro_val in self.clib_intf.macros:
            # handle special case, where function macros are defined without
            # parenthesis:
            # #define FNMACRO1(x) x+1
            # #define FNMACRO2 FNMACRO1     //FNMACRO2 is a function macro!!!
            macro = self.clib_intf.macros[macro_val]
            self.clib_intf.add_macro(t.macro, macro, self.cur_file_name)
            logger.debug("  Copy fnmacro {} => {}".format(macro_val, t.macro))

        else:
            if t.args == '':
                macro = c_model.ValMacro(macro_val)
                val = self.eval_expr(macro_val)
                self.clib_intf.macro_vals[t.macro] = val
                mess = "  Add macro: {} ({}); {}"
                logger.debug(mess.format(t.macro, val, macro))

            else:
                fnmacro = c_model.FnMacro(macro_val, list(t.args))
                self.clib_intf.add_macro(t.macro, fnmacro, self.cur_file_name)
                mess = "  Add fn macro: {} ({}); {}"
                logger.debug(mess.format(t.macro, t.args, fnmacro))

        self.clib_intf.add_macro(t.macro, macro, self.cur_file_name)
        return macro.c_repr(t.macro)

    def expand_macros(self, line):
        """Expand all the macro expressions in a string.

        Faulty calls to macro function are left untouched.

        """
        reg = re.compile(
            r'("(\\"|[^"])*")|'
            '(([a-zA-Z0-9' + self.supported_ident_non_alnums + ']+))')
        parts = []
        # The group number to check for macro names
        N = 3
        while True:
            m = reg.search(line)
            if not m:
                break
            name = m.groups()[N]
            if name in self.clib_intf.macros:
                macro = self.clib_intf.macros[name]
                if isinstance(macro, c_model.ValMacro):
                    parts.append(line[:m.start(N)])
                    line = line[m.end(N):]
                    parts.append(macro.content)

                elif isinstance(macro, c_model.FnMacro):
                    # If function macro expansion fails, just ignore it.
                    try:
                        exp, end = self.expand_fn_macro(name, line[m.end(N):])
                    except Exception:
                        exp = name
                        end = 0
                        mess = "Function macro expansion failed: {}, {}"
                        logger.error(mess.format(name, line[m.end(N):]))

                    parts.append(line[:m.start(N)])
                    start = end + m.end(N)
                    line = line[start:]
                    parts.append(exp)

            else:
                start = m.end(N)
                parts.append(line[:start])
                line = line[start:]

        parts.append(line)
        return ''.join(parts)

    def expand_fn_macro(self, name, text):
        """Replace a function macro.

        """
        arg_list = (stringStart +
                    self.lparen +
                    Group(delimitedList(self.expression))('args') +
                    self.rparen)
        res = [x for x in arg_list.scanString(text, 1)]
        if len(res) == 0:
            mess = "Function macro '{}' not followed by (...)"
            raise DefinitionError(0,  mess.format(name))

        args, start, end = res[0]
        exp_args = [self.expand_macros(arg) for arg in args[0]]
        new_str = self.clib_intf.macros[name].parametrized_content(*exp_args)

        return (new_str, end)

    # --- Compilation functions

    def parse(self, srccode, pack_list):
        """Scan through the named file for variable, struct, enum, and function
        declarations.

        Parameters
        ----------
        srccode : str
            Preprocessed Sourcecode, that will be analysed and added to
            self.clib_intf

        pack_list : list[tuple[int, int]]
            a list of line ranges with the according struct packings
            (#pragma pack). All structs defined within a specific range
            use the according packing.

        Returns
        -------
        tokens : list
            Entire tree of successfully parsed tokens.

        """
        self.cur_pack_list = pack_list
        try:
            return [x[0] for x in self.parser.scanString(srccode)]
        finally:
            self.cur_pack_list = None

    # Syntatic delimiters
    comma = Literal(",").ignore(quotedString).suppress()
    colon = Literal(":").ignore(quotedString).suppress()
    semi = Literal(";").ignore(quotedString).suppress()
    lbrace = Literal("{").ignore(quotedString).suppress()
    rbrace = Literal("}").ignore(quotedString).suppress()
    lbrack = Literal("[").ignore(quotedString).suppress()
    rbrack = Literal("]").ignore(quotedString).suppress()
    lparen = Literal("(").ignore(quotedString).suppress()
    rparen = Literal(")").ignore(quotedString).suppress()

    # Numbers
    int_strip = lambda t: t[0].rstrip('UL')
    hexint = Regex('[+-]?\s*0[xX][{}]+[UL]*'.format(hexnums)).setParseAction(int_strip)
    decint = Regex('[+-]?\s*[0-9]+[UL]*').setParseAction(int_strip)
    integer = (hexint | decint)
    # The floating regex is ugly but it is because we do not want to match
    # integer to it.
    floating = Regex(r'[+-]?\s*((((\d(\.\d*)?)|(\.\d+))[eE][+-]?\d+)|((\d\.\d*)|(\.\d+)))')
    number = (floating | integer)

    # Miscelaneous
    bi_operator = oneOf("+ - / * | & || && ! ~ ^ % == != > < >= <= -> . :: << >> = ? :")
    uni_right_operator = oneOf("++ --")
    uni_left_operator = oneOf("++ -- - + * sizeof new")

    supported_base_types = ['int', 'char', 'void', 'float', 'double', 'bool']
    supported_sign_modifiers = ['unsigned', 'signed']
    supported_size_modifiers = ['short', 'long']
    supported_storage_classes = ['static', 'extern', 'inline']
    supported_type_qualifiers = ['const', 'volatile', 'restrict',]
    supported_ident_non_alnums = '_'

    @property
    def keyword(self):
        """A ParserElement of all keywords"""
        keywords = (['struct', 'enum', 'union'] +
                    self.supported_type_qualifiers +
                    self.supported_storage_classes +
                    self.supported_base_types +
                    self.supported_size_modifiers +
                    self.supported_sign_modifiers)

        return self._kwl(list(self.filter_no_par(keywords)) +
                         list(self.filter_par(keywords)))

    def generic_ident(self, exceptions=None):
        """A generic ParserElement for identificators. In C this are all words
        not beginning with numbers.
        The ParserElement 'exception' allows to specify a list of not
        accepted identificators.

        Can be overwritten by descendant to allow only specific ID patterns.
        """
        result = WordStart(alphas + self.supported_ident_non_alnums)
        if exceptions is not None:
            result += ~exceptions
        result += Word(alphas + self.supported_ident_non_alnums,
                       alphanums + self.supported_ident_non_alnums)
        result += WordEnd(alphanums + self.supported_ident_non_alnums)
        return result.setParseAction(self._converter(str))

    @staticmethod
    def _kwl(strs):
        """Generate a match-first list of keywords given a list of strings."""
        regex = '|'.join(strs)
        if len(regex) == 0:
            return NoMatch()
        else:
            return Regex(r'\b({})\b'.format(regex))
    
    
    @staticmethod
    def _converter(converterFunc):
        """Flattens a tree of tokens and joins into one big string and
        converts the str by 'converterFunc'.

        """
        def flatten(lst):
            res = []
            for i in lst:
                if isinstance(i, (list, tuple)):
                    res.extend(flatten(i))
                else:
                    res.append(str(i))
            return res

        def recombine(tok):
            return converterFunc(' '.join(flatten(tok.asList())))

        return recombine

    @staticmethod
    def filter_par(kwds):
        """returns all keywords, that end with '(...)', but without '(...)'"""
        for kwd in kwds:
            if kwd.endswith('(...)'):
                yield kwd[:-len('(...)')]

    @staticmethod
    def filter_no_par(kwds):
        """returns all keywords, that do not end with '(...)'"""
        for kwd in kwds:
            if not kwd.endswith('(...)'):
                yield kwd

    @staticmethod
    def _print_parse_results(pr, depth=0, name=''):
        """For debugging; pretty-prints parse result objects.
    
        """
        start = name + " " * (20 - len(name)) + ':' + '..' * depth
        if isinstance(pr, ParseResults):
            print(start)
            for i in pr:
                name = ''
                for k in pr.keys():
                    if pr[k] is i:
                        name = k
                        break
                CParser._print_parse_results(i, depth+1, name)
        else:
            print(start + str(pr))
    
    def _build_parser(self):
        """Builds the entire tree of parser elements for the C language (the
        bits we support, anyway).

        """
        def mergeNested(t):
            return ''.join((part if isinstance(part, basestring)
                            else '(' + mergeNested(part) + ')')
                           for part in t)

        ident = self.generic_ident(exceptions=self.keyword)

        self.type_qualifier = ZeroOrMore(
            (self._kwl(self.filter_par(self.supported_type_qualifiers)) +
             Optional(nestedExpr())).setParseAction(mergeNested) |
            self._kwl(self.filter_no_par(self.supported_type_qualifiers)))

        self.storage_class_spec = ZeroOrMore(
            (self._kwl(self.filter_par(self.supported_storage_classes)) +
             Optional(nestedExpr())).setParseAction(mergeNested) |
            self._kwl(self.filter_no_par(self.supported_storage_classes)))

        # Language elements
        self.fund_type = OneOrMore(
            self._kwl(self.supported_sign_modifiers +
                      self.supported_size_modifiers +
                      self.supported_base_types)
        ).setParseAction(lambda t: ' '.join(t))

        self.expression = Forward()

        # Is there a better way to process expressions with cast operators??
        cast_atom = (
            ZeroOrMore(self.uni_left_operator) +
            Optional('('+ident+')').suppress() +
            ((ident + '(' + Optional(delimitedList(self.expression)) +
                ')' |
              ident + OneOrMore('[' + self.expression + ']') |
              ident |
              self.number |
              quotedString
              ) |
             ('(' + self.expression + ')')) +
            ZeroOrMore(self.uni_right_operator)
            )

        # XXX Added name here to catch macro functions on types
        uncast_atom = (
            ZeroOrMore(self.uni_left_operator) +
            ((ident + '(' + Optional(delimitedList(self.expression)) +
                ')' |
              ident + OneOrMore('[' + self.expression + ']') |
              ident |
              self.number |
              self.generic_ident() |
              quotedString
              ) |
             ('(' + self.expression + ')')) +
            ZeroOrMore(self.uni_right_operator)
            )

        atom = cast_atom | uncast_atom

        self.expression << Group(atom + ZeroOrMore(self.bi_operator + atom))
        self.expression.setParseAction(self._converter(str))

        if hasattr(self, 'parser'):
            return self.parser

        self.struct_type = Forward()
        self.enum_type = Forward()
        custom_type = ident.copy()
        type_astdef = (
            self.fund_type.setParseAction(
                self._converter(c_model.BuiltinType)) |
            custom_type.setParseAction(self._converter(c_model.CustomType)) |
            self.struct_type |
            self.enum_type)
        self.type_spec = self.type_qualifier('pre_qual') + type_astdef('type')

        # --- Abstract declarators for use in function pointer arguments
        #   Thus begins the extremely hairy business of parsing C declarators.
        #   Whomever decided this was a reasonable syntax should probably never
        #   breed.
        #   The following parsers combined with the process_declarator function
        #   allow us to turn a nest of type modifiers into a correctly
        #   ordered list of modifiers.

        self.declarator = Forward()
        self.abstract_declarator = Forward()

        #  Abstract declarators look like:
        #     <empty string>
        #     *
        #     **[num]
        #     (*)(int, int)
        #     *( )(int, int)[10]
        #     ...etc...
        self.abstract_declarator << Group(
            Group(ZeroOrMore(
                Group(self.type_qualifier + Suppress('*'))))('ptrs') +
            self.type_qualifier('qual') +
            Optional((self.lparen +
                      self.abstract_declarator +
                      self.rparen)('center')) +
            Optional(self.lparen +
                     Optional(delimitedList(Group(
                              self.type_spec +
                              self.abstract_declarator('decl') +
                              Optional(Literal('=').suppress() +
                                       self.expression,
                                       default=None)('val')
                              )), default=None) +
                     self.rparen)('args') +
            Group(ZeroOrMore(self.lbrack +
                             Optional(self.expression, default='') +
                  self.rbrack))('arrays')
        )

        # Declarators look like:
        #     varName
        #     *varName
        #     **varName[num]
        #     (*fnName)(int, int)
        #     * fnName(int arg1=0)[10]
        #     ...etc...
        self.declarator << Group(
            Group(ZeroOrMore(Group(self.type_qualifier +
                                   Suppress('*'))))('ptrs') +
            self.type_qualifier('qual') +
            (ident('name') |
             (self.lparen + self.declarator + self.rparen)('center')) +
            Optional(self.lparen +
                     Optional(delimitedList(
                         Group(self.type_spec +
                               (self.declarator |
                                self.abstract_declarator)('decl') +
                               Optional(Literal('=').suppress() +
                                        self.expression, default=None)('val')
                               )),
                              default=None) +
                     self.rparen)('args') +
            Group(ZeroOrMore(self.lbrack +
                             Optional(self.expression, default='') +
                             self.rbrack))('arrays')
        )
        self.declarator_list = Group(delimitedList(self.declarator))

        # Typedef
        self.type_decl = (Keyword('typedef') + self.type_spec +
                          self.declarator_list('decl_list') + self.semi)
        self.type_decl.setParseAction(self.process_typedef)

        # Variable declaration
        self.variable_decl = (
            Group(self.type_qualifier('pre_qual') +
                  self.storage_class_spec('pre_stor_cls') +
                  type_astdef('type') +
                  self.storage_class_spec('post_stor_cls') +
                  Optional(self.declarator_list('decl_list')) +
                  Optional(Literal('=').suppress() +
                           (self.expression('value') |
                            (self.lbrace +
                             Group(delimitedList(self.expression)
                                   )('array_values') +
                             self.rbrace
                             )
                            )
                           )
                  ) +
            self.semi)
        self.variable_decl.setParseAction(self.process_variable)

        # Function definition
        self.function_decl = (
            self.type_qualifier('pre_qual') +
            self.storage_class_spec('pre_stor_cls') +
            type_astdef('type') +
            self.storage_class_spec('post_stor_cls') +
            self.declarator('decl') +
            nestedExpr('{', '}').suppress())
        self.function_decl.setParseAction(self.process_function)

        # Struct definition
        self.struct_decl = Forward()
        struct_kw = (Keyword('struct') | Keyword('union'))
        self.struct_member = (
            Group(self.variable_decl.copy().setParseAction(lambda: None)) |
            # Hack to handle bit width specification.
            Group(Group(self.type_spec +
                        Optional(self.declarator_list('decl_list')) +
                        self.colon + self.integer('bit') + self.semi)) |
            (self.type_spec + self.declarator +
             nestedExpr('{', '}')).suppress() |
            (self.declarator + nestedExpr('{', '}')).suppress()
            )

        self.decl_list = (self.lbrace +
                          Group(OneOrMore(self.struct_member))('members') +
                          self.rbrace)
        self.struct_type << (struct_kw('struct_type') +
                             ((Optional(ident('name')) +
                               self.decl_list) | ident('name'))
                             )
        self.struct_type.setParseAction(self.process_compound)

        self.struct_decl = self.struct_type + self.semi

        # Enum definition
        enum_var_decl = Group(ident('name') +
                              Optional(Literal('=').suppress() +
                              (self.integer('value') |
                               ident('valueName'))))

        self.enum_type << (Keyword('enum') +
                           ((Optional(ident('name')) +
                             self.lbrace +
                             Group(delimitedList(enum_var_decl))('members') +
                             Optional(self.comma) +
                             self.rbrace) |
                            ident('name'))
                           )
        self.enum_type.setParseAction(self.process_enum)
        self.enum_decl = self.enum_type + self.semi

        self.parser = (self.type_decl | self.variable_decl |
                       self.function_decl)
        return self.parser

    def process_declarator(self, decl, base_type):
        """Process a declarator (without base type) and return a tuple
        (name, [modifiers])

        See process_type(...) for more information.

        """
        name = None
        quals = list(decl.get('qual', []))
        logger.debug("DECL: {}".format(decl))

        if 'ptrs' in decl and len(decl['ptrs']) > 0:
            for ptr_level in decl['ptrs']:
                base_type = c_model.PointerType(
                    base_type.with_quals(list(ptr_level)))

        if 'args' not in decl or len(decl['args']) == 0:
            base_type = base_type.with_quals(quals)
        else:
            if decl['args'][0] is None:
                params = []
            else:
                params = [self.process_type(a, a['decl'])
                          for a in decl['args']]
            base_type = c_model.FunctionType(base_type, params, quals)

        if 'arrays' in decl and len(decl['arrays']) > 0:
            for ast_arrsize in reversed(decl['arrays']):
                arrsize = (self.eval_expr(ast_arrsize) if ast_arrsize != ''
                           else None)
                base_type = c_model.ArrayType(base_type, arrsize)

        if 'center' in decl:
            (n, base_type) = self.process_declarator(
                decl['center'][0],
                base_type)
            if n is not None:
                name = n

        if 'name' in decl:
            name = decl['name']

        return (name, base_type)

    def process_type(self, type_ast, decl):
        """Take a declarator + base type and return a CLibType object.
        """
        pre_quals = list(type_ast.get('pre_qual', []))
        base_type = type_ast.get('type').with_quals(pre_quals)
        logger.debug("PROCESS TYPE/DECL: {}".format(base_type))
        return self.process_declarator(decl, base_type)

    def process_enum(self, s, l, t):
        """
        """
        try:
            logger.debug("ENUM: {}".format(t))
            ename = 'enum ' + t.name if t.name else None

            logger.debug("  name: {}".format(ename))

            if ename not in self.clib_intf.typedefs:
                enum_vals = []
                cur_enum_val = 0
                for v in t.members:
                    if v.value != '':
                        cur_enum_val = literal_eval(v.value)
                    if v.valueName != '':
                        cur_enum_val = dict(enum_vals)[v.valueName]
                    enum_vals.append((v.name, cur_enum_val))
                    cur_enum_val += 1
                logger.debug("  members: {}".format(enum_vals))

                etyp = c_model.EnumType(enum_vals)
                if not ename:
                    return etyp
                else:
                    self.clib_intf.add_typedef(ename, etyp, self.cur_file_name)

            return c_model.CustomType(ename)
        except:
            logger.exception("Error processing enum: {}".format(t))

    def process_function(self, s, l, t):
        """Build a function definition from the parsing tokens.

        """
        logger.debug("FUNCTION {} : {}".format(t, t.keys()))

        try:
            (name, func_sig) = self.process_type(t, t.decl[0])
            storage_classes = (list(t.pre_stor_cls or []) +
                               list(t.post_stor_cls or []))
            if not isinstance(func_sig, c_model.FunctionType):
                logger.error('{}'.format(t))
                mess = "Incorrect declarator type for function definition."
                raise DefinitionError(mess)
            logger.debug("  sig/name: {}".format(func_sig.c_repr(name)))
            self.clib_intf.add_func(name, func_sig, self.cur_file_name,
                                    storage_classes)

        except Exception:
            logger.exception("Error processing function: {}".format(t))

    def packing_at(self, line):
        """Return the structure packing value at the given line number.

        """
        packing = None
        for p in self.cur_pack_list:
            if p[0] <= line:
                packing = p[1]
            else:
                break
        return packing

    def process_compound(self, s, l, t):
        """
        """
        try:
            str_typ = t.struct_type  # struct or union

            # Check for extra packing rules
            packing = self.packing_at(lineno(l, s))

            logger.debug('{} {} {}'.format(str_typ.upper(), t.name, t))
            sname = str_typ + ' ' + t.name if t.name else None

            logger.debug("  NAME: {}".format(sname))
            if len(t.members) > 0 or sname not in self.clib_intf.typedefs:
                logger.debug("  NEW " + str_typ.upper())
                fields = []
                for m in t.members:
                    typ = m[0]
                    val = self.eval_expr(m[0].value)
                    logger.debug("    member: {}, {}, {}".format(
                                 m, m[0].keys(), m[0].decl_list))

                    if len(m[0].decl_list) == 0:  # anonymous member
                        if str_typ == 'struct':
                            field = (None, typ.type, None)
                        else:
                            field = (None, typ.type)
                        fields.append(field)

                    for d in m[0].decl_list:
                        (name, field_type) = self.process_type(typ, d)

                        if str_typ == 'struct':
                            bitsize = int(m[0].bit) if m[0].bit else None
                            field = (name, field_type, bitsize)
                        else:
                            bitsize = None
                            field = (name, field_type)
                        fields.append(field)

                        logger.debug("      {0[0]} {0[1]} {1} {2}".format(
                            field, val, bitsize))

                if str_typ == 'struct':
                    type_ = c_model.StructType(fields, packing)
                else:
                    type_ = c_model.UnionType(fields)

                if sname is None:
                    # anonymous struct/union => return directly
                    return type_
                else:
                    self.clib_intf.add_typedef(sname, type_,
                                               self.cur_file_name)

            return c_model.CustomType(sname)

        except Exception:
            logger.exception('Error processing struct: {}'.format(t))

    def process_variable(self, s, l, t):
        """
        """
        logger.debug("VARIABLE: {}".format(t))
        try:
            val = self.eval_expr(t[0])
            for d in t[0].decl_list:
                (name, type_) = self.process_type(t[0], d)
                # This is a function prototype
                storage_classes = (list(t[0].pre_stor_cls or []) +
                                   list(t[0].post_stor_cls or []))
                if isinstance(type_, c_model.FunctionType):
                    logger.debug("  Add function prototype: {}".format(
                                 type_.c_repr(name)))
                    self.clib_intf.add_func(name, type_, self.cur_file_name,
                                            storage_classes)
                # This is a variable
                else:
                    logger.debug("  Add variable: {} {} {}".format(name,
                                 type_, val))
                    self.clib_intf.add_var(name, type_, self.cur_file_name,
                                           storage_classes)

        except Exception:
            logger.exception('Error processing variable: {}'.format(t))

    def process_typedef(self, s, l, t):
        """
        """
        logger.debug("TYPE: {}".format(t))
        for d in t.decl_list:
            (name, type_) = self.process_type(t, d)
            logger.debug("  {}: {}".format(name, type_))
            self.clib_intf.add_typedef(name, type_, self.cur_file_name)

    # --- Utility methods

    def eval_expr(self, toks):
        """Evaluates expressions.

        Currently only works for expressions that also happen to be valid
        python expressions.

        """
        logger.debug("Eval: {}".format(toks))
        try:
            if istext(toks) or isbytes(toks):
                val = self.eval(toks, None, self.clib_intf.macro_vals)
            elif toks.array_values != '':
                val = [self.eval(x, None, self.clib_intf.macro_vals)
                       for x in toks.array_values]
            elif toks.value != '':
                val = self.eval(toks.value, None, self.clib_intf.macro_vals)
            else:
                val = None
            return val

        except Exception:
            logger.debug("    failed eval {} : {}".format(toks, format_exc()))
            return None

    def eval(self, expr, *args):
        """Just eval with a little extra robustness."""
        expr = expr.strip()
        cast = (self.lparen + self.type_spec + self.abstract_declarator +
                self.rparen).suppress()
        expr = (quotedString | self.number | cast).transformString(expr)
        if expr == '':
            return None
        return eval(expr, *args)


class MSVCParser(CParser):
    """A CParser that takes the MicroSoft Visual C extensions into account.
    These are:

    - the '__int64' type
    - additional type qualifiers like __cdecl, __stdcall, __restrict, ...
    - the __declspec(), __inline and __forceinline extensions
    - allows usage of '$' in  identifier names
    - additional predefines like '_MSC_VER'

    Parameters
    ----------
    header_dirs : list[str], optional
        same as CParser

    predef_macros : dict[str, str], optional
        same as CParser

    msc_ver : int, optional
        The C compiler version that shall be emulated (usually 1500 for
        version 15.00)

    arch : int, optional
        The architecture of the backend. Can be 32 or 64 (bits).

    """

    supported_base_types = CParser.supported_base_types + [
        '__int64']
    supported_type_qualifiers = CParser.supported_type_qualifiers + [
        '__based', '__cdecl', '__fastcall', '__stdcall', '__restrict',
        '__sptr', '__uptr', '__ptr64', '__w64', '__allowed(...)']
    supported_storage_classes = CParser.supported_storage_classes + [
        '__declspec(...)', '__forceinline', '__inline']
    supported_ident_non_alnums = '_$'

    def __init__(self, header_dirs=None, predef_macros=None,
                 msc_ver=1500, arch=32):
        ms_predef_macros={}
        ms_predef_macros['_MSC_VER'] = str(msc_ver)
        if arch == 32:
            ms_predef_macros['_M_IX86'] = ''
        elif arch == 64:
            ms_predef_macros['_M_AMD64'] = ''
        else:
            raise ValueError("'arch' has to be either 32 (=32 bit "
                             "architecture) or 64 (=64 bit architecture)")
        if predef_macros:
            ms_predef_macros.update()
        super(MSVCParser, self).__init__(header_dirs, ms_predef_macros)
