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

from .errors import DefinitionError
from .utils import find_header
from pyclibrary import c_model

# Import parsing elements
from .thirdparty.pyparsing import \
    (ParserElement, ParseResults, Forward, Optional, Word, WordStart,
     WordEnd, Keyword, Regex, Literal, SkipTo, ZeroOrMore, OneOrMore,
     Group, LineEnd, stringStart, quotedString, oneOf, nestedExpr,
     delimitedList, restOfLine, cStyleComment, alphas, alphanums, hexnums,
     lineno, Suppress)
ParserElement.enablePackrat()

logger = logging.getLogger(__name__)


__all__ = ['win_defs', 'CParser']


def win_defs(version='1500'):
    """Loads selection of windows headers included with PyCLibrary.

    These definitions can either be accessed directly or included before
    parsing another file like this:
    >>> windefs = win_defs()
    >>> p = CParser("headerFile.h", copy_from=windefs)

    Definitions are pulled from a selection of header files included in Visual
    Studio (possibly not legal to distribute? Who knows.), some of which have
    been abridged because they take so long to parse.

    Parameters
    ----------
    version : unicode
        Version of the MSVC to consider when parsing.

    Returns
    -------
    parser : CParser
        CParser containing all the infos from te windows headers.

    """
    header_files = ['WinNt.h', 'WinDef.h', 'WinBase.h', 'BaseTsd.h',
                    'WTypes.h', 'WinUser.h']
    if not CParser._init:
        logger.warning('Automatic initialisation : OS is assumed to be win32')
        from .init import auto_init
        auto_init()
    d = os.path.dirname(__file__)
    p = CParser(
        header_files,
        macros={'_WIN32': '', '_MSC_VER': version, 'CONST': 'const',
                'NO_STRICT': None, 'MS_WIN32': ''},
        process_all=False
        )

    p.process_all(cache=os.path.join(d, 'headers', 'WinDefs.cache'))

    return p


class CParser(object):
    """Class for parsing C code to extract variable, struct, enum, and function
    declarations as well as preprocessor macros.

    This is not a complete C parser; instead, it is meant to simplify the
    process of extracting definitions from header files in the absence of a
    complete build system. Many files will require some amount of manual
    intervention to parse properly (see 'replace' and extra arguments)

    Parameters
    ----------
    files : str or iterable, optional
        File or files which should be parsed.

    copy_from : CLibInterface, that shall be used as template for this parsers
        .clib_intf

    replace : dict, optional
        Specify som string replacements to perform before parsing. Format is
        {'searchStr': 'replaceStr', ...}

    process_all : bool, optional
        Flag indicating whether files should be parsed immediatly. True by
        default.

    cache : unicode, optional
        Path of the cache file from which to load definitions/to which save
        definitions as parsing is an expensive operation.

    kwargs :
        Extra macros may be used to specify the starting state of the
        parser: WINAPI='', TESTMACRO='3'

    Example
    -------
    Create parser object, load two files

    >>> p = CParser(['header1.h', 'header2.h'])

    Remove comments, preprocess, and search for declarations

    >>> p.process_ all()

    Just to see what was successfully parsed from the files

    >>> p.print_all()

    Access parsed declarations

    >>> p.clib_intf

    To see what was not successfully parsed

    >>> unp = p.process_all(return_unparsed=True)
    >>> for s in unp:
            print s

    """
    #: Increment every time cache structure or parsing changes to invalidate
    #: old cache files.
    cache_version = 2

    #: Private flag allowing to know if the parser has been initiliased.
    _init = False

    def __init__(self, files=None, copy_from=None, replace=None,
                 process_all=True, cache=None, **kwargs):

        self.clib_intf = c_model.CLibInterface()
        if copy_from is not None:
            self.clib_intf.include(copy_from)
        self.macro_vals = {}

        if not self._init:
            logger.warning('Automatic initialisation based on OS detection')
            from .init import auto_init
            auto_init()

        # Description of the struct packing rules as defined by #pragma pack
        self.pack_list = {}

        self.init_opts = kwargs.copy()
        self.init_opts['files'] = []
        self.init_opts['replace'] = {}

        self.file_order = []
        self.files = {}

        if files is not None:
            if istext(files) or isbytes(files):
                files = [files]
            for f in self.find_headers(files):
                self.load_file(f, replace)

        self.current_file = None

        # Import extra macros if specified
        for name, value in kwargs:
            self.clib_intf.add_macro(name, c_model.ValMacro(value))

        if process_all:
            self.process_all(cache=cache)

    def process_all(self, cache=None, return_unparsed=False,
                    print_after_preprocess=False):
        """ Remove comments, preprocess, and parse declarations from all files.

        This operates in memory, and thus does not alter the original files.

        Parameters
        ----------
        cache : unicode, optional
            File path where cached results are be stored or retrieved. The
            cache is automatically invalidated if any of the arguments to
            __init__ are changed, or if the C files are newer than the cache.
        return_unparsed : bool, optional
           Passed directly to parse_defs.

        print_after_preprocess : bool, optional
            If true prints the result of preprocessing each file.

        Returns
        -------
        results : list
            List of the results from parse_defs.

        """
        if cache is not None and self.load_cache(cache, check_validity=True):
            logger.debug("Loaded cached definitions; will skip parsing.")
            # Cached values loaded successfully, nothing left to do here
            return

        results = []
        logger.debug(cleandoc('''Parsing C header files (no valid cache found).
                              This could take several minutes...'''))
        for f in self.file_order:

            if self.files[f] is None:
                # This means the file could not be loaded and there was no
                # cache.
                mess = 'Could not find header file "{}" or a cache file.'
                raise IOError(mess.format(f))

            logger.debug("Removing comments from file '{}'...".format(f))
            self.remove_comments(f)

            logger.debug("Preprocessing file '{}'...".format(f))
            self.preprocess(f)

            if print_after_preprocess:
                print("===== PREPROCSSED {} =======".format(f))
                print(self.files[f])

            logger.debug("Parsing definitions in file '{}'...".format(f))

            results.append(self.parse_defs(f, return_unparsed))

        if cache is not None:
            logger.debug("Writing cache file '{}'".format(cache))
            self.write_cache(cache)

        return results

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
        result : bool
            Did the loading succeeded.

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
                return False

        # Make sure cache is newer than all input files
        if check_validity:
            mtime = os.stat(cache_file).st_mtime
            for f in self.file_order:
                # If file does not exist, then it does not count against the
                # validity of the cache.
                if os.path.isfile(f) and os.stat(f).st_mtime > mtime:
                    logger.debug("Cache file is out of date.")
                    return False

        try:
            # Read cache file
            import pickle
            cache = pickle.load(open(cache_file, 'rb'))

            # Make sure __init__ options match
            if check_validity:
                if cache['opts'] != self.init_opts:
                    db = logger.debug
                    db("Cache file is not valid")
                    db("It was created using different initialization options")
                    db('{}'.format(cache['opts']))
                    db('{}'.format(self.init_opts))
                    return False

                else:
                    logger.debug("Cache init opts are OK:")
                    logger.debug('{}'.format(cache['opts']))

                if cache['version'] < self.cache_version:
                    mess = "Cache file is not valid--cache format has changed."
                    logger.debug(mess)
                    return False

            # Import all parse results
            self.clib_intf.include(cache['clib_intf'])
            return True

        except Exception:
            logger.exception("Warning--cache read failed:")
            return False

    def write_cache(self, cache_file):
        """Store all parsed declarations to cache. Used internally.

        """
        cache = {}
        cache['opts'] = self.init_opts
        cache['clib_intf'] = self.clib_intf
        cache['version'] = self.cache_version
        import pickle
        pickle.dump(cache, open(cache_file, 'wb'))

    def find_headers(self, headers):
        """Try to find the specified headers.

        """
        hs = []
        for header in headers:
            if os.path.isfile(header):
                hs.append(header)
            else:
                h = find_header(header)
                if not h:
                    raise OSError('Cannot find header: {}'.format(header))
                hs.append(h)

        return hs

    def load_file(self, path, replace=None):
        """Read a file, make replacements if requested.

        Called by __init__, should not be called manually.

        Parameters
        ----------
        path : unicode
            Path of the file to load.

        replace : dict, optional
            Dictionary containing strings to replace by the associated value
            when loading the file.

        """
        if not os.path.isfile(path):
            # Not a fatal error since we might be able to function properly if
            # there is a cache file.
            mess = "Warning: C header '{}' is missing, this may cause trouble."
            logger.warning(mess.format(path))
            self.files[path] = None
            return False

        # U causes all newline types to be converted to \n
        with open(path, 'rU') as fd:
            self.files[path] = fd.read()

        if replace is not None:
            for s in replace:
                self.files[path] = re.sub(s, replace[s], self.files[path])

        self.file_order.append(path)
        bn = os.path.basename(path)
        self.init_opts['replace'][bn] = replace
        # Only interested in the file names, the directory may change between
        # systems.
        self.init_opts['files'].append(bn)
        return True

    # =========================================================================
    # --- Processing functions
    # =========================================================================

    def remove_comments(self, path):
        """Remove all comments from file.

        Operates in memory, does not alter the original files.

        """
        text = self.files[path]
        cplusplus_line_comment = Literal("//") + restOfLine
        # match quoted strings first to prevent matching comments inside quotes
        comment_remover = (quotedString | cStyleComment.suppress() |
                           cplusplus_line_comment.suppress())
        self.files[path] = comment_remover.transformString(text)

    # --- Pre processing

    def preprocess(self, path):
        """Scan named file for preprocessor directives, removing them while
        expanding macros.

        Operates in memory, does not alter the original files.

        Currently support :
        - conditionals : ifdef, ifndef, if, elif, else (defined can be used
        in a if statement).
        - definition : define, undef
        - pragmas : pragma

        """
        # We need this so that eval_expr works properly
        self.build_parser()
        self.current_file = path

        # Stack for #pragma pack push/pop
        pack_stack = [(None, None)]
        self.pack_list[path] = [(0, None)]
        packing = None  # Current packing value

        text = self.files[path]

        # First join together lines split by \\n
        text = Literal('\\\n').suppress().transformString(text)

        # Macro the structure of a macro definition
        name = Word(alphas+'_', alphanums+'_')('name')
        deli_list = Optional(lparen + delimitedList(name) + rparen)
        self.pp_define = (name.setWhitespaceChars(' \t')("macro") +
                          deli_list.setWhitespaceChars(' \t')('args') +
                          SkipTo(LineEnd())('value'))
        self.pp_define.setParseAction(self.process_macro_defn)

        # Comb through lines, process all directives
        lines = text.split('\n')

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
                            (name | lparen + name + rparen)
                            ).setParseAction(pa).transformString(rest)

                elif d in ['define', 'undef']:
                    match = re.match(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)(.*)$', rest)
                    macroName, rest = match.groups()

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
                    if not if_true[-1]:
                        continue
                    logger.debug("  "*(len(if_true)-1) + "define: " +
                                 '{}, {}'.format(macroName, rest))
                    try:
                        # Macro is registered here
                        self.pp_define.parseString(macroName + ' ' + rest)
                    except Exception:
                        logger.exception("Error processing macro definition:" +
                                         '{}, {}'.format(macroName, rest))

                elif d == 'undef':
                    if not if_true[-1]:
                        continue
                    try:
                        self.clib_intf.del_macro(macroName.strip())
                    except Exception:
                        if sys.exc_info()[0] is not KeyError:
                            mess = "Error removing macro definition '{}'"
                            logger.exception(mess.format(macroName.strip()))

                # Check for changes in structure packing
                # Support only for #pragme pack (with all its variants
                # save show), None is used to signal that the default packing
                # is used.
                # Those two definition disagree :
                # https://gcc.gnu.org/onlinedocs/gcc/Structure-Packing-Pragmas.html
                # http://msdn.microsoft.com/fr-fr/library/2e70t5y1.aspx
                # The current implementation follows the MSVC doc.
                elif d == 'pragma':
                    if not if_true[-1]:
                        continue
                    m = re.match(r'\s+pack\s*\(([^\)]*)\)', rest)
                    if not m:
                        continue
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
                    self.pack_list[path].append((i, packing))
                else:
                    # Ignore any other directives
                    mess = 'Ignored directive {} at line {}'
                    logger.debug(mess.format(d, i))

            result.append(new_line)
        self.files[path] = '\n'.join(result)

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
            self.clib_intf.add_macro(t.macro, macro, self.current_file)
            logger.debug("  Copy fnmacro {} => {}".format(macro_val, t.macro))

        else:
            if t.args == '':
                macro = c_model.ValMacro(macro_val)
                val = self.eval_expr(macro_val)
                self.macro_vals[t.macro] = val
                mess = "  Add macro: {} ({}); {}"
                logger.debug(mess.format(t.macro, val, macro))

            else:
                fnmacro = c_model.FnMacro(macro_val, list(t.args))
                self.clib_intf.add_macro(t.macro, fnmacro, self.current_file)
                mess = "  Add fn macro: {} ({}); {}"
                logger.debug(mess.format(t.macro, t.args, fnmacro))

        self.clib_intf.add_macro(t.macro, macro, self.current_file)
        return macro.c_repr(t.macro)
    
    ###TODO: remove, as it moved to FnMacro._compiled_content
    def compile_fn_macro(self, text, args):
        """Turn a function macro spec into a compiled description.

        """
        # Find all instances of each arg in text.
        args_str = '|'.join(args)
        arg_regex = re.compile(r'("(\\"|[^"])*")|(\b({})\b)'.format(args_str))
        start = 0
        parts = []
        arg_order = []
        # The group number to check for macro names
        N = 3
        for m in arg_regex.finditer(text):
            arg = m.groups()[N]
            if arg is not None:
                parts.append(text[start:m.start(N)] + '{}')
                start = m.end(N)
                arg_order.append(args.index(arg))
        parts.append(text[start:])
        return (''.join(parts), arg_order)

    def expand_macros(self, line):
        """Expand all the macro expressions in a string.

        Faulty calls to macro function are left untouched.

        """
        reg = re.compile(r'("(\\"|[^"])*")|(\b(\w+)\b)')
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
        arg_list = (stringStart + lparen +
                    Group(delimitedList(expression))('args') + rparen)
        res = [x for x in arg_list.scanString(text, 1)]
        if len(res) == 0:
            mess = "Function macro '{}' not followed by (...)"
            raise DefinitionError(0,  mess.format(name))

        args, start, end = res[0]
        exp_args = [self.expand_macros(arg) for arg in args[0]]
        new_str = self.clib_intf.macros[name].parametrized_content(*exp_args)

        return (new_str, end)

    # --- Compilation functions

    def parse_defs(self, path, return_unparsed=False):
        """Scan through the named file for variable, struct, enum, and function
        declarations.

        Parameters
        ----------
        path : unicode
            Path of the file to parse for definitions.

        return_unparsed : bool, optional
            If true, return a string of all lines that failed to match (for
            debugging purposes).

        Returns
        -------
        tokens : list
            Entire tree of successfully parsed tokens.

        """
        self.current_file = path

        parser = self.build_parser()
        if return_unparsed:
            text = parser.suppress().transformString(self.files[path])
            return re.sub(r'\n\s*\n', '\n', text)
        else:
            return [x[0] for x in parser.scanString(self.files[path])]

    def build_parser(self):
        """Builds the entire tree of parser elements for the C language (the
        bits we support, anyway).

        """
        if hasattr(self, 'parser'):
            return self.parser

        self.struct_type = Forward()
        self.enum_type = Forward()
        type_astdef = (
            fund_type.setParseAction(converter(c_model.BuiltinType)) |
            (Optional(kwl(size_modifiers + sign_modifiers)) + ident).setParseAction(converter(c_model.CustomType)) | ###TODO: check if modifiers can be omitted, since not part of C standard
            self.struct_type |
            self.enum_type)
        self.type_spec = type_qualifier('pre_qual') + type_astdef('type')

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
            Group(ZeroOrMore(Group(type_qualifier + Suppress('*'))))('ptrs') +
            type_qualifier('qual') +
            Optional((lparen + self.abstract_declarator + rparen)('center')) +
            Optional(lparen +
                     Optional(delimitedList(Group(
                              self.type_spec('type_spec') +
                              self.abstract_declarator('decl') +
                              Optional(Literal('=').suppress() + expression,
                                       default=None)('val')
                              )), default=None) +
                     rparen)('args') +
            Group(ZeroOrMore(lbrack + Optional(expression, default='') +
                  rbrack))('arrays')
        )

        # Declarators look like:
        #     varName
        #     *varName
        #     **varName[num]
        #     (*fnName)(int, int)
        #     * fnName(int arg1=0)[10]
        #     ...etc...
        self.declarator << Group(
            Group(ZeroOrMore(Group(type_qualifier + Suppress('*'))))('ptrs') +
            type_qualifier('qual') +
            (ident('name') |
             (lparen + self.declarator + rparen)('center')) +
            Optional(lparen +
                     Optional(delimitedList(
                         Group(self.type_spec('type_spec') +
                               (self.declarator |
                                self.abstract_declarator)('decl') +
                               Optional(Literal('=').suppress() +
                               expression, default=None)('val')
                               )),
                              default=None) +
                     rparen)('args') +
            Group(ZeroOrMore(lbrack + Optional(expression, default='') +
                             rbrack))('arrays')
        )
        self.declarator_list = Group(delimitedList(self.declarator))

        # Typedef
        self.type_decl = (Keyword('typedef') + self.type_spec('type_spec') +
                          self.declarator_list('decl_list') + semi)
        self.type_decl.setParseAction(self.process_typedef)

        # Variable declaration
        self.variable_decl = (
            Group(storage_class_spec +
                  self.type_spec('type_spec') +
                  Optional(self.declarator_list('decl_list')) +
                  Optional(Literal('=').suppress() +
                           (expression('value') |
                            (lbrace +
                             Group(delimitedList(expression))('array_values') +
                             rbrace
                             )
                            )
                           )
                  ) +
            semi)
        self.variable_decl.setParseAction(self.process_variable)

        # Function definition
        self.typeless_function_decl = (self.declarator('decl') +
                                       nestedExpr('{', '}').suppress())
        self.function_decl = (storage_class_spec +
                              self.type_spec('type_spec') +
                              self.declarator('decl') +
                              nestedExpr('{', '}').suppress())
        self.function_decl.setParseAction(self.process_function)

        # Struct definition
        self.struct_decl = Forward()
        struct_kw = (Keyword('struct') | Keyword('union'))
        self.struct_member = (
            Group(self.variable_decl.copy().setParseAction(lambda: None)) |
            # Hack to handle bit width specification.
            Group(Group(self.type_spec('type_spec') +
                        Optional(self.declarator_list('decl_list')) +
                        colon + integer('bit') + semi)) |
            (self.type_spec + self.declarator +
             nestedExpr('{', '}')).suppress() |
            (self.declarator + nestedExpr('{', '}')).suppress()
            )

        self.decl_list = (lbrace +
                          Group(OneOrMore(self.struct_member))('members') +
                          rbrace)
        self.struct_type << (struct_kw('struct_type') +
                             ((Optional(ident('name')) +
                               self.decl_list) | ident('name'))
                             )
        self.struct_type.setParseAction(self.process_compound)

        self.struct_decl = self.struct_type + semi

        # Enum definition
        enum_var_decl = Group(ident('name') +
                              Optional(Literal('=').suppress() +
                              (integer('value') | ident('valueName'))))

        self.enum_type << (Keyword('enum') +
                           (Optional(ident('name')) +
                            lbrace +
                            Group(delimitedList(enum_var_decl))('members') +
                            Optional(comma) + rbrace | ident('name'))
                           )
        self.enum_type.setParseAction(self.process_enum)
        self.enum_decl = self.enum_type + semi

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
                params = [self.process_type(a['type_spec'], a['decl'])
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
            if t.name == '':
                n = 0   ###TODO: replace by anonymous enum counter in clibinterface
                while True:
                    name = 'anon_enum{}'.format(n)   ###TODO: rename to '$'+nr to avoid name clashes
                    if ('enum ' + name) not in self.clib_intf.typedefs:
                        break
                    n += 1
            else:
                name = t.name

            logger.debug("  name: {}".format(name))

            if ('enum ' + name) not in self.clib_intf.typedefs:
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
                self.clib_intf.add_typedef('enum ' + name,
                                           c_model.EnumType(enum_vals),
                                           self.current_file)
            return c_model.CustomType('enum ' + name)
        except:
            logger.exception("Error processing enum: {}".format(t))

    def process_function(self, s, l, t):
        """Build a function definition from the parsing tokens.

        """
        logger.debug("FUNCTION {} : {}".format(t, t.keys()))

        try:
            (name, ret_type) = self.process_type(t.type_spec, t.decl[0])
            if not isinstance(ret_type, c_model.FunctionType):
                logger.error('{}'.format(t))
                mess = "Incorrect declarator type for function definition."
                raise DefinitionError(mess)
            logger.debug("  sig/name: {}".format(ret_type.c_repr(name)))
            self.clib_intf.add_func(name, ret_type, self.current_file)

        except Exception:
            logger.exception("Error processing function: {}".format(t))

    def packing_at(self, line):
        """Return the structure packing value at the given line number.

        """
        packing = None
        for p in self.pack_list[self.current_file]:
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
            if t.name == '':
                n = 0 ###TODO: replace by anonymous enum counter in clibinterface
                while True:
                    sname = '{0} anon_{0}{1}'.format(str_typ, n)
                    if sname not in self.clib_intf.typedefs:
                        break
                    n += 1
            else:
                sname = str_typ + ' ' + t.name

            logger.debug("  NAME: {}".format(sname))
            if (len(t.members) > 0 or sname not in self.clib_intf.typedefs or
                    self.clib_intf.typedefs[sname].fields == {}):
                logger.debug("  NEW " + str_typ.upper())
                fields = []
                for m in t.members:
                    typ = m[0].type_spec
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
                self.clib_intf.add_typedef(sname, type_, self.current_file)

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
                (name, type_) = self.process_type(t[0].type_spec, d)
                # This is a function prototype
                if isinstance(type_, c_model.FunctionType):
                    logger.debug("  Add function prototype: {}".format(
                                 type_.c_repr(name)))
                    self.clib_intf.add_func(name, type_, self.current_file)
                # This is a variable
                else:
                    logger.debug("  Add variable: {} {} {}".format(name,
                                 type_, val))
                    self.clib_intf.add_var(name, type_, self.current_file)

        except Exception:
            logger.exception('Error processing variable: {}'.format(t))

    def process_typedef(self, s, l, t):
        """
        """
        logger.debug("TYPE: {}".format(t))
        ast_type = t.type_spec
        for d in t.decl_list:
            (name, type_) = self.process_type(ast_type, d)
            logger.debug("  {}: {}".format(name, type_))
            self.clib_intf.add_typedef(name, type_, self.current_file)

    # --- Utility methods

    def eval_expr(self, toks):
        """Evaluates expressions.

        Currently only works for expressions that also happen to be valid
        python expressions.

        """
        logger.debug("Eval: {}".format(toks))
        try:
            if istext(toks) or isbytes(toks):
                val = self.eval(toks, None, self.macro_vals)
            elif toks.array_values != '':
                val = [self.eval(x, None, self.macro_vals)
                       for x in toks.array_values]
            elif toks.value != '':
                val = self.eval(toks.value, None, self.macro_vals)
            else:
                val = None
            return val

        except Exception:
            logger.debug("    failed eval {} : {}".format(toks, format_exc()))
            return None

    def eval(self, expr, *args):
        """Just eval with a little extra robustness."""
        expr = expr.strip()
        cast = (lparen + self.type_spec + self.abstract_declarator +
                rparen).suppress()
        expr = (quotedString | number | cast).transformString(expr)
        if expr == '':
            return None
        return eval(expr, *args)

    def find_text(self, text):
        """Search all file strings for text, return matching lines.

        """
        res = []
        for f in self.files:
            l = self.files[f].split('\n')
            for i in range(len(l)):
                if text in l[i]:
                    res.append((f, i, l[i]))
        return res


# --- Basic parsing elements.

def kwl(strs):
    """Generate a match-first list of keywords given a list of strings."""
    return Regex(r'\b({})\b'.format('|'.join(strs)))


def flatten(lst):
        res = []
        for i in lst:
            if isinstance(i, (list, tuple)):
                res.extend(flatten(i))
            else:
                res.append(str(i))
        return res


def converter(converter):
    """Flattens a tree of tokens and joins into one big string and converts
    the str by 'converter'.
    """
    def recombine(tok):
        return converter(' '.join(flatten(tok.asList())))
    return recombine


def print_parse_results(pr, depth=0, name=''):
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
            print_parse_results(i, depth+1, name)
    else:
        print(start + str(pr))


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
wordchars = alphanums+'_$'
name = (WordStart(wordchars) + Word(alphas+"_", alphanums+"_$") +
        WordEnd(wordchars))
size_modifiers = ['short', 'long']
sign_modifiers = ['signed', 'unsigned']

# Syntax elements defined by _init_parser.
expression = Forward()
array_op = lbrack + expression + rbrack
base_types = None
ident = None
type_qualifier = None
storage_class_spec = None
fund_type = None
extra_type_list = []

num_types = ['int', 'float', 'double']
nonnum_types = ['char', 'bool', 'void']


# Macro some common language elements when initialising.
def _init_cparser(extra_types=None, extra_modifiers=()):
    global expression
    global ident
    global base_types
    global type_qualifier, storage_class_spec
    global fund_type
    global extra_type_list

    # Some basic definitions
    extra_type_list = [] if extra_types is None else list(extra_types)
    base_types = nonnum_types + num_types + extra_type_list
    storage_classes = ['inline', 'static', 'extern']
    ###TODO: extend storage classes by stanard and custom ones (i.e. 'auto', 'register', '__declspec()')
    ###TODO: allow storage classes to be intermixed with types (i.e. int static a')
    qualifiers = ['const', 'volatile', 'restrict', 'near', 'far', '__cdecl', '__stdcall', 'call_conv']

    keywords = (['struct', 'enum', 'union', '__stdcall', '__cdecl'] +
                qualifiers + base_types + size_modifiers + sign_modifiers)

    keyword = kwl(keywords)
    wordchars = alphanums+'_$'
    ident = (WordStart(wordchars) + ~keyword +
             Word(alphas + "_", alphanums + "_$") +
             WordEnd(wordchars)).setParseAction(lambda t: t[0])

    # Removes '__name' from all type specs. may cause trouble.
    underscore_2_ident = (WordStart(wordchars) + ~keyword + '__' +
                          Word(alphanums, alphanums+"_$") +
                          WordEnd(wordchars)
                          )

    special_quals = underscore_2_ident   ###TODO: remove / has to be done via extra_modifiers in future
    if extra_modifiers:
        special_quals |= kwl(extra_modifiers)
    def mergeNested(t):
        return ''.join((part if isinstance(part, basestring)
                        else '(' + mergeNested(part) + ')')
                       for part in t)
    type_qualifier = ZeroOrMore(
        (special_quals + Optional(nestedExpr())).setParseAction(mergeNested) |
        kwl(qualifiers))

    storage_class_spec = Optional(kwl(storage_classes))

    # Language elements
    fund_type = OneOrMore(kwl(sign_modifiers + size_modifiers +
                          base_types)).setParseAction(lambda t: ' '.join(t))

    # Is there a better way to process expressions with cast operators??
    cast_atom = (
        ZeroOrMore(uni_left_operator) + Optional('('+ident+')').suppress() +
        ((ident + '(' + Optional(delimitedList(expression)) + ')' |
          ident + OneOrMore('[' + expression + ']') |
          ident | number | quotedString
          ) |
         ('(' + expression + ')')) +
        ZeroOrMore(uni_right_operator)
        )

    # XXX Added name here to catch macro functions on types
    uncast_atom = (
        ZeroOrMore(uni_left_operator) +
        ((ident + '(' + Optional(delimitedList(expression)) + ')' |
          ident + OneOrMore('[' + expression + ']') |
          ident | number | name | quotedString
          ) |
         ('(' + expression + ')')) +
        ZeroOrMore(uni_right_operator)
        )

    atom = cast_atom | uncast_atom

    expression << Group(atom + ZeroOrMore(bi_operator + atom))
    expression.setParseAction(converter(str))


###TODO: remove this and adapt interface of CParser
class NewCParser(object):
    """
    This object shall replace CParser in future.
    """

    def __init__(self, cust_type_quals=None, stdlib_hdrs=None):
        """
        creates a parser object, that is customized for a specific
        compiler (i.e. the microsoft compiler will support different
        type_quals than GCC
        """
        pass

    def derive(self, stdlib_hdrs):
        """
        create a cloned parser with different stdlib

        :param stdlib_hdrs:
        :return:
        """
        pass

    def parse(self, hdr_files):
        clibIntf = c_model.CLibInterface()

        for hdr_file in hdr_files:
            if isinstance(hdr_file, basestring):
                hdr_file = open(hdr_file, "rt")

            # parse types, macrodefs and global objects of hdr_file into clib_intf

        return clibIntf
