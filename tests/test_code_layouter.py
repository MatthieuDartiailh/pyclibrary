# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2015 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
import pytest
from pyclibrary import c_model as cm, code_layouter
from io import StringIO


MAX_COLUMN = 80
BIGTOKEN = 'x'*(MAX_COLUMN+1)
ENDTOKEN = ' LSE'
STARTTOKEN = 'LSS '

class TestCode(object):

    @pytest.fixture
    def default_cl(self):
        out_file = StringIO()
        default_cl = code_layouter.CodeLayouter(out_file)
        return default_cl

    @pytest.yield_fixture
    def limited_cl(self, default_cl):
        with default_cl.layout(max_col=MAX_COLUMN) as limited_cl:
            yield limited_cl

    @pytest.yield_fixture
    def esc_cl(self, limited_cl):
        with limited_cl.layout(linesplit_tokens=(ENDTOKEN, STARTTOKEN)) as cl:
            yield cl

    def output_of(self, default_cl):
        default_cl.close()
        return default_cl.out_file.getvalue()

    def test_allMethods_returnSelf(self, default_cl):
        assert default_cl.tokens() == default_cl
        assert default_cl.nl() == default_cl
        assert default_cl.space() == default_cl

    def test_tokens_onMultipleCall_writeConcatenatedToFile(self, default_cl):
        default_cl.tokens('xx').tokens('yy')
        assert self.output_of(default_cl) == 'xxyy'

    def test_tokens_onSingleCallWithMultipleParams_writeToFile(self, default_cl):
        default_cl.tokens('xx', 'yy')
        assert self.output_of(default_cl) == 'xxyy'

    def test_nl_onNoArgs_insertsSingleNewLine(self, default_cl):
        default_cl.nl()
        assert self.output_of(default_cl) == '\n'

    def test_nl_withLineCount_insertsMultipleNewLine(self, default_cl):
        default_cl.nl(3)
        assert self.output_of(default_cl) == 3*'\n'

    def test_nl_onSetIndent_autoInsertsSpaceAtNewLine(self, default_cl):
        default_cl.indent = 8
        default_cl.tokens('test').nl().tokens('x').nl()
        assert self.output_of(default_cl) == '        test\n        x\n'

    def test_minVDist_onNlCount0_insertsASingleNlToEnsureSeparateLine(self, default_cl):
        default_cl.tokens('aa')
        default_cl.min_vdist(0)
        default_cl.tokens('b')
        assert self.output_of(default_cl) == 'aa\nb'

    def test_minVDist_onNoMoreTokens_insertsASingleNlOnly(self, default_cl):
        default_cl.tokens('test')
        default_cl.min_vdist(5)
        assert self.output_of(default_cl) == 'test'

    def test_minVDist_calledBetweenToklens_insertsSpecifiedAmountOfNls(self, default_cl):
        default_cl.tokens('xxxx')
        default_cl.min_vdist(3)
        default_cl.tokens('yy')
        assert self.output_of(default_cl) == 'xxxx\n\n\n\nyy'

    def test_minVDist_calledMultipleTimes_onlyBiggestValueIsConsidered(self, default_cl):
        default_cl.tokens('xxxx')
        default_cl.min_vdist(2).min_vdist(3).min_vdist(1)
        default_cl.tokens('yy')
        assert self.output_of(default_cl) == 'xxxx\n\n\n\nyy'

    def test_minVDist_intermixWithNl_considersAlreayAddedNlsWhenAddingMinVDist(self, default_cl):
        default_cl.tokens('xxxx')
        default_cl.nl()
        default_cl.min_vdist(3)
        default_cl.nl()
        default_cl.tokens('yy')
        assert self.output_of(default_cl) == 'xxxx\n\n\n\nyy'

    def test_minVDist_intermixWithMoreNlsThanMinVDist_ignoresMinVDist(self, default_cl):
        default_cl.tokens('xxxx')
        default_cl.nl(2)
        default_cl.min_vdist(1)
        default_cl.nl()
        default_cl.tokens('yy')
        assert self.output_of(default_cl) == 'xxxx\n\n\nyy'

    def test_curCol_afterWrites_returnsAddedStringLens(self, default_cl):
        default_cl.tokens('1234').tokens('567')
        assert default_cl.cur_col == 7

    def test_curCol_onIndentBeforeFirstToken_isZero(self, default_cl):
        default_cl.indent = 8
        default_cl.tokens('')
        assert default_cl.cur_col == 0

    def test_curCol_onIndentafterFirstToken_isIndented(self, default_cl):
        default_cl.indent = 8
        default_cl.tokens('x')
        assert default_cl.cur_col == 9

    def test_layout_withIndent_changesIndentTemporarly(self, default_cl):
        with default_cl.layout(indent=3) as indented_cl:
            assert indented_cl.indent == 3
            with indented_cl.layout(rel_indent=-1) as indented2_cl:
                assert indented2_cl.indent == 2
            assert indented_cl.indent == 3
        assert default_cl.indent == 0

    def test_layout_withMaxCol_changesMaxColTemporarly(self, default_cl):
        with default_cl.layout(max_col=10) as limited_cl:
            assert limited_cl.max_col == 10
            with limited_cl.layout(max_col=None) as resetted_cl:
                assert resetted_cl.max_col == None
            assert limited_cl.max_col == 10
        assert default_cl.max_col == None

    def test_layout_withLineSplitTokens_changesLineSplitTokensTemporarly(self, default_cl):
        with default_cl.layout(linesplit_tokens=(ENDTOKEN, STARTTOKEN)) as \
                escaped_cl:
            assert escaped_cl.linesplit_start_token == STARTTOKEN
            assert escaped_cl.linesplit_end_token == ENDTOKEN
            with escaped_cl.layout() as nochange_cl:
                assert nochange_cl.linesplit_start_token == STARTTOKEN
                assert nochange_cl.linesplit_end_token == ENDTOKEN
        assert default_cl.linesplit_start_token == ''
        assert default_cl.linesplit_end_token == ''

    def test_tokens_onMultipleCallsExceedingMaxCol_splitLine(self, limited_cl):
        limited_cl.tokens('x', 'y', 'z'*MAX_COLUMN)
        assert limited_cl.cur_col == MAX_COLUMN
        assert self.output_of(limited_cl) == 'xy\n' + 'z'*MAX_COLUMN

    def test_tokens_toMaxColFollowedByEmptyWrite_doesNothing(self, default_cl):
        default_cl.tokens('x'*MAX_COLUMN, '')
        assert self.output_of(default_cl) == 'x'*MAX_COLUMN

    def test_tokens_onMultipleCallsPerLimitedLine_splitsAtLastTokenendBeforeMaxCol(self, limited_cl):
        limited_cl.tokens('x'*(MAX_COLUMN-1), '1', '2', '3')
        assert self.output_of(limited_cl) == 'x'*(MAX_COLUMN-1) + '1\n23'

    def test_tokens_onMultipleCallsPerUnlimitedLine_doesNotSplitLine(self, default_cl):
        for cnt in range(3):
            default_cl.tokens(BIGTOKEN)
        assert self.output_of(default_cl) == BIGTOKEN * 3

    def test_tokens_onEscLine_insertsLineSplitTokens(self, esc_cl):
        for cnt in range(MAX_COLUMN+1):
            esc_cl.tokens('x')
        assert (self.output_of(esc_cl) ==
                'x'*(MAX_COLUMN-len(ENDTOKEN)) + ENDTOKEN + '\n' +
                STARTTOKEN + 'x'*(len(ENDTOKEN)+1))

    def test_tokens_onEscLineWithBigToken_insertsTokensOnSplittedLine(self, esc_cl):
        esc_cl.tokens(BIGTOKEN).tokens('x')
        assert (self.output_of(esc_cl) ==
                BIGTOKEN + ENDTOKEN + '\n' + STARTTOKEN + 'x')

    def test_tokens_onEscLineWithIndent_insertsStartTokenAfterIndent(self, esc_cl):
        with esc_cl.layout(4) as indented_esc_cl:
            indented_esc_cl.tokens(BIGTOKEN)
            indented_esc_cl.tokens('x')
        assert (self.output_of(esc_cl) ==
                (' '*4 + BIGTOKEN + ENDTOKEN + '\n' +
                 ' '*4 + STARTTOKEN + 'x'))

    def test_nl_onEndToken_doesNotInsertEndToken(self, default_cl):
        self.linesplit_end_token = ENDTOKEN
        default_cl.tokens('x'*MAX_COLUMN).nl().tokens('y')
        assert self.output_of(default_cl) == 'x'*MAX_COLUMN + '\ny'

    def test_nl_afterTokenendAtMaxCol_splitsOnlyOnce(self, default_cl):
        default_cl.tokens('1'*MAX_COLUMN).nl()
        assert self.output_of(default_cl) == '1'*MAX_COLUMN + '\n'

    def test_space_withinLine_insertsBlanks(self, default_cl):
        default_cl.tokens('xx').space(MAX_COLUMN-5).space().tokens('yy')
        assert self.output_of(default_cl) == 'xx' + ' '*(MAX_COLUMN-4) + 'yy'

    def test_space_atBeginOfLine_ignored(self, default_cl):
        default_cl.space(MAX_COLUMN+1).tokens('y')
        assert self.output_of(default_cl) == 'y'

    def test_space_onLimitedLineAddSpaceToEndOfLineFollowedByTokenOrNl_splitsLine(self, limited_cl):
        limited_cl.tokens('x')
        limited_cl.space(MAX_COLUMN-1).tokens('y')
        limited_cl.space(MAX_COLUMN-1).nl()
        assert self.output_of(limited_cl) == 'x\ny\n'

    def test_space_onLimitedLineAddSpaceUntilMaxCol_splitsLineWithoutInsertSpace(self, limited_cl):
        limited_cl.tokens('x').space(MAX_COLUMN-1).tokens('y')
        assert self.output_of(limited_cl) == 'x\ny'

    def test_space_onFollowedByEmptyWrite_doesNotSplit(self, default_cl):
        default_cl.tokens('x').space(MAX_COLUMN-1).tokens('')
        assert self.output_of(default_cl) == 'x'

    def test_space_onEscLineWithSpaceOnMaxCol_removesSpacesBeforeEndToken(self, esc_cl):
        esc_cl.tokens('x' * (MAX_COLUMN-len(ENDTOKEN)))
        esc_cl.space(10)
        esc_cl.space(10)
        esc_cl.tokens('y')
        assert (self.output_of(esc_cl) ==
                ('x'*(MAX_COLUMN-len(ENDTOKEN)) + ENDTOKEN + '\n' +
                 STARTTOKEN + 'y'))
    def test_minHDist_onSpaceCount0_insertsNothing(self, default_cl):
        default_cl.tokens('aa')
        default_cl.min_hdist(0)
        default_cl.tokens('b')
        assert self.output_of(default_cl) == 'aab'

    def test_minHDist_onNoMoreTokens_insertsNoSpace(self, default_cl):
        default_cl.tokens('test')
        default_cl.min_hdist(5)
        assert self.output_of(default_cl) == 'test'

    def test_minHDist_calledBetweenTokens_insertsSpecifiedAmountOfSpaces(self, default_cl):
        default_cl.tokens('xxxx')
        default_cl.min_hdist(3)
        default_cl.tokens('yy')
        assert self.output_of(default_cl) == 'xxxx' + ' '*3 + 'yy'

    def test_minHDist_calledMultipleTimes_onlBiggestValueIsConsidered(self, default_cl):
        default_cl.tokens('xxxx')
        default_cl.min_hdist(2).min_hdist(3).min_hdist(1)
        default_cl.tokens('yy')
        assert self.output_of(default_cl) == 'xxxx' + ' '*3 + 'yy'

    def test_minHDist_intermixWithSpace_considersAlreayAddedSpacesWhenAddingMinHDist(self, default_cl):
        default_cl.tokens('xxxx')
        default_cl.space()
        default_cl.min_hdist(3)
        default_cl.space()
        default_cl.tokens('yy')
        assert self.output_of(default_cl) == 'xxxx' + ' '*3 + 'yy'

    def test_minHDist_intermixWithMoreSpacesThanMinVDist_ignoresMinHDist(self, default_cl):
        default_cl.tokens('xxxx')
        default_cl.space(2)
        default_cl.min_hdist(1)
        default_cl.space()
        default_cl.tokens('yy')
        assert self.output_of(default_cl) == 'xxxx' + ' '*3 + 'yy'


    def test_curCol_afterSpaces_returnsAddedSpaceCount(self, default_cl):
        default_cl.tokens('x').space().space(9)
        assert default_cl.cur_col == 11

    def test_del_closeFlushesBuffers(self):
        out_file = StringIO()
        cl = code_layouter.CodeLayouter(out_file)
        cl.tokens('test')
        del cl
        assert out_file.getvalue() == 'test'
