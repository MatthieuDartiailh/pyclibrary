# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Provides a simple code layouting engine.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
import contextlib


class CodeLayouter(object):
    """Provides functionality for layouting code on token level.
    This includes indentation and automatic line breaking.
    Furthermore escape tokens on line break are configurable and minimum
    spaces / lines can be set here.

    It is even possible to change the settings for parts of the code with the
    context 'layout()', that returns a modified codelayouter until it is
    finished.

    Parameters
    ----------
    out_file: file
        file, where result is written into. As CodeLayouter buffers the
        current line, out_file is not updated until CodeLayouter is closed.

    """

    def __init__(self, out_file):
        self.out_file = out_file
        self.max_col = None
        self.indent = 0
        self.cur_line = []
        self.cur_line_marker = []
        self.closed = False
        self.linesplit_end_token = ''
        self.linesplit_start_token = ''
        self.split_ndx = None
        self.min_nl_count = 0
        self.nl_count = 0
        self.min_space_count = 0
        self.space_count = 0

    @contextlib.contextmanager
    def layout(self, rel_indent=0, indent=None, max_col=0,
               linesplit_tokens=None):
        """A context that can be used to change the layoutsettings as
        indentation, maximum line width and escape linesplit tokens

        Paramters
        ---------
        rel_indent: int, optional
            A relative change of the current value of 'indent'
            (if indent is specified this this value is ignored)

        indent, int, optional
            An absolute value for the indentation in columns. The first token
            of every line within the context will start at the given column.

        max_col: int|None, optional
            if None, code lines may be of arbitrary length.
            On any positive integer, code lines bigger than than max_col
            will be splitted, so that no line is exceeds max_col columns
            (excluded '\n').
            The only exception is, if a line consists of only a songle
            token that exceeds the length of max_col.

        linesplit: tuple of two strings, optional
            If a linesplit is enforced since a line is exceeding
            'max_col' columns the first string of this tuple is inserted
            at the end of the first line and the second one at the beginning
            (but after indentation) of the second line.

        """
        indent_backup = self.indent
        max_col_backup = self.max_col
        linesplit_start_token_backup = self.linesplit_start_token
        linesplit_end_token_backup = self.linesplit_end_token

        self.indent = (indent or (self.indent + rel_indent))
        if max_col != 0:
            self.max_col = max_col
        if linesplit_tokens:
            self.linesplit_end_token, self.linesplit_start_token = \
                linesplit_tokens

        yield self

        self.max_col = max_col_backup
        self.indent = indent_backup
        self.linesplit_start_token = linesplit_start_token_backup
        self.linesplit_end_token = linesplit_end_token_backup

    def __remove_trailing_spaces(self):
        while self.cur_line_marker and self.cur_line_marker.pop():
            self.cur_line.pop()

    def __flush(self):
        self.__remove_trailing_spaces()
        self.out_file.write(''.join(self.cur_line))
        del self.cur_line[:]
        del self.cur_line_marker[:]
        self.split_ndx = None

    def close(self):
        """Closes the code layouter and flushes all buffered tokens to the
        outstream.

        """
        if not self.closed:
            self.__flush()
            self.closed = True

    def __del__(self):
        self.close()

    def tokens(self, *tokens):
        """Writes an arbitrary number of tokens to the outstream.

        Parameters
        ----------
        *tokens : tuple of strings
            Strings that will be written to the outputfile. The strings
            (=token) will never be splitted by the layouter.
            Strings that may be splitted have to be passed as two separate
            parameters instead of a single one.

        """
        assert not self.closed

        if tokens:
            if self.min_nl_count > self.nl_count:
                self.nl(self.min_nl_count - self.nl_count)
            self.min_nl_count = 0
            self.nl_count = 0

            if self.min_space_count > self.space_count:
                self.space(self.min_space_count - self.space_count)
            self.min_space_count = 0
            self.space_count = 0

        for token in tokens:
            if len(token) > 0:
                if len(self.cur_line) == 0:
                    self.cur_line.append(' ' * self.indent)
                    self.cur_line_marker.append(True)
                elif (self.split_ndx is None and self.max_col is not None and
                        self.cur_col + len(token) >
                            self.max_col - len(self.linesplit_end_token)):
                    self.split_ndx = len(self.cur_line)
                self.cur_line.append(token)
                self.cur_line_marker.append(False)

            if (self.max_col is not None and
                    len(self.cur_line) > 2 and
                    self.cur_col > self.max_col):
                # remove tokens, that do not fit together with esc token
                new_line = self.cur_line[self.split_ndx:]
                new_line_marker = self.cur_line_marker[self.split_ndx:]
                self.cur_line = self.cur_line[:self.split_ndx]
                self.cur_line_marker = self.cur_line_marker[:self.split_ndx]

                self.__remove_trailing_spaces()
                self.cur_line.append(self.linesplit_end_token) ###
                self.cur_line_marker.append(False)
                self.nl()
                new_line.insert(0, self.linesplit_start_token)
                new_line_marker.insert(0, False) ###

                # insert tokens from previous line
                for tok, tok_marker in zip(new_line, new_line_marker):
                    if tok_marker:
                        self.space(len(tok))
                    else:
                        self.tokens(tok)

        return self

    def nl(self, count=1):
        """Finish writing the current code line and start a new one.
        WHen explicitly enfocing a new line no linesplit_tokens will be
        inserted!

        Parameters
        ----------
        count: int, optional
            Number of newlines to add (instead of 1)

        """
        self.__flush()
        self.out_file.write('\n' * count)
        self.nl_count += count
        return self

    def min_vdist(self, nl_count):
        """Specifies the minimum amount of empty lines between this token
        and the next one. If called multiple times
        (i.E. cl.min_vdist(2).min_vdist(3)) only the biggest value
        will be used for generating newlines.

        If mixed with nl() the nl-calls are considered when calling min_vdist.
        I.e. the following min_vdist() will add only 3 newlines, as 2
        were already added by nl():

            cl.nl().min_vdist(5).nl()

        Parameters
        ----------
        nl_count: int
            minimum number of empty lines between the previous and the next
            token

        """
        self.min_nl_count = max(self.min_nl_count, 1 + nl_count)
        return self

    def space(self, count=1):
        """Inserts one (or multiple) spaces after the last inserted token.
        If space is inserted at the beginning of a line or at the end of a
        line it is ignored!

        Parameters
        ----------
        count: int, optional
            Number of blanks to add (instead of 1)

        """
        if len(self.cur_line) > 0:
            self.cur_line.append(' '*count)
            self.cur_line_marker.append(True)
            self.space_count += count
        return self

    def min_hdist(self, space_count):
        """Specifies the minimum amount of empty spaces between this token
        and the next one. If called multiple times
        (i.E. cl.min_vdist(2).min_vdist(3)) only the biggest value
        will be used for generating newlines.

        If mixed with space() the space-calls are considered when calling
        min_hdist.
        I.e. the following min_hdist() will add only 3 spaces, as 2
        were already added by space():

            cl.space().min_hdist(5).space()

        Parameters
        ----------
        space_count: int
            minimum number of empty spaces between the previous and the next
            token

        """
        self.min_space_count = max(self.min_space_count, space_count)
        return self

    @property
    def cur_col(self):
        """Returns the current column.

        """
        return sum(map(len, self.cur_line))
