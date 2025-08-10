# -----------------------------------------------------------------------------
# Copyright 2015-2022 by PyCLibrary Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT/X11 license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Test parser functionalities."""

import os
import sys
from pickle import dumps, loads

import pyclibrary.utils
import pytest
from pyclibrary.c_parser import CParser, Enum, Struct, Type, Union

H_DIRECTORY = os.path.join(os.path.dirname(__file__), "headers")


def compare_lines(lines, lines2):
    """Compare lines striped from whitespaces characters."""
    for line, line_test in zip(lines, lines2):
        assert line.strip() == line_test.strip()


class TestType(object):
    def test_init(self):
        with pytest.raises(ValueError):
            Type("int", "*", type_quals=(("volatile",),))

    def test_tuple_equality(self):
        assert Type("int") == ("int",)
        assert ("int",) == Type("int")

        assert Type("int", "*", type_quals=[["const"], ["volatile"]]) == ("int", "*")

        assert issubclass(Type, tuple)

    def test_Type_equality(self):
        assert Type("int", "*", type_quals=(("const",), ("volatile",))) == Type(
            "int", "*", type_quals=(("const",), ("volatile",))
        )
        assert Type("int", "*", type_quals=(("const",), ())) != Type(
            "int", "*", type_quals=(("const",), ("volatile",))
        )

    def test_getters(self):
        assert Type("int", "*").type_spec == "int"
        assert Type("int", "*", [1]).declarators == ("*", [1])
        assert Type("int", "*", type_quals=(("volatile",), ())).type_quals == (
            ("volatile",),
            (),
        )

    def test_is_fund_type(self):
        assert not Type("custom_typedef").is_fund_type()

        assert Type("int").is_fund_type()
        assert Type("int", "*").is_fund_type()
        assert Type("int", [1]).is_fund_type()
        assert Type("int", ()).is_fund_type()
        assert Type("int", type_quals=(("volatile",))).is_fund_type()
        assert Type("struct test").is_fund_type()

        assert Type("unsigned").is_fund_type()
        assert Type("short").is_fund_type()
        assert Type("unsigned short int").is_fund_type()

        assert Type("bool").is_fund_type()
        assert Type("char").is_fund_type()
        assert Type("wchar").is_fund_type()
        assert Type("wchar_t").is_fund_type()
        assert Type("unsigned char").is_fund_type()
        assert Type("short").is_fund_type()
        assert Type("short int").is_fund_type()
        assert Type("unsigned short").is_fund_type()
        assert Type("unsigned short int").is_fund_type()
        assert Type("int").is_fund_type()
        assert Type("unsigned").is_fund_type()
        assert Type("unsigned int").is_fund_type()
        assert Type("long").is_fund_type()
        assert Type("long int").is_fund_type()
        assert Type("unsigned long").is_fund_type()
        assert Type("unsigned long int").is_fund_type()
        assert Type("long unsigned int").is_fund_type()
        assert Type("long long").is_fund_type()
        assert Type("long long int").is_fund_type()
        assert Type("unsigned long long").is_fund_type()
        assert Type("unsigned long long int").is_fund_type()
        assert Type("float").is_fund_type()
        assert Type("double").is_fund_type()
        assert Type("long double").is_fund_type()
        assert Type("uint8_t").is_fund_type()
        assert Type("int8_t").is_fund_type()
        assert Type("uint16_t").is_fund_type()
        assert Type("int16_t").is_fund_type()
        assert Type("uint32_t").is_fund_type()
        assert Type("int32_t").is_fund_type()
        assert Type("uint64_t").is_fund_type()
        assert Type("int64_t").is_fund_type()
        assert Type("size_t").is_fund_type()
        assert Type("ssize_t").is_fund_type()

        if sys.version_info >= (3, 12):
            assert Type("time_t").is_fund_type()

        if sys.platform == "win32":
            assert Type("__int64").is_fund_type()
            assert Type("unsigned __int64").is_fund_type()

    def test_eval(self):
        type_map = {
            "tq_parent_type": Type("int", "*", type_quals=(("__tq1",), ("__tq2",))),
            "parent_type": Type("int", "*", "*", [2]),
            "child_type": Type("parent_type", "*", [3]),
        }

        assert Type("parent_type", "*", [1]).eval(type_map) == Type(
            "int", "*", "*", [2], "*", [1]
        )
        assert Type("child_type", (), "*").eval(type_map) == Type(
            "int", "*", "*", [2], "*", [3], (), "*"
        )
        assert Type("tq_parent_type", [1], type_quals=(("__tq3",), ("__tq4",))).eval(
            type_map
        ) == Type(
            "int", "*", [1], type_quals=(("__tq1",), ("__tq2", "__tq3"), ("__tq4",))
        )

    def test_compatibility_hack(self):
        assert Type("int", "*", ()).add_compatibility_hack() == Type(
            Type("int", "*"), ()
        )
        assert Type("int", "*", (), "*").add_compatibility_hack() == Type(
            "int", "*", (), "*"
        )
        assert Type(
            "int", (), type_quals=(("const",), ("__interrupt",))
        ).add_compatibility_hack() == Type(
            Type("int", type_quals=(("const",),)),
            (),
            type_quals=(
                (),
                ("__interrupt",),
            ),
        )

        assert Type(Type("int", "*"), ()).remove_compatibility_hack() == Type(
            "int", "*", ()
        )
        assert Type("int", "*", ()).remove_compatibility_hack() == Type("int", "*", ())

    def test_repr(self):
        assert repr(Type("int", "*")) == "Type({!r}, {!r})".format("int", "*")
        assert repr(Type("int", "*", type_quals=(("volatile",), ()))) == (
            "Type({!r}, {!r}, type_quals=(({!r},), ()))".format("int", "*", "volatile")
        )

    def test_persistence(self):
        t = Type("tq_parent_type", [1], type_quals=(("__tq3",), ("__tq4",)))
        assert repr(t) == repr(loads(dumps(t)))


class TestStructUnion(object):
    TEST_MEMBERS = [("a", Type("int"), None), ("b", Type("char", "*"), None)]

    def test_init(self):
        assert Struct().members == []
        assert Struct().pack is None
        assert Struct(*self.TEST_MEMBERS).members == self.TEST_MEMBERS
        assert Struct(pack=2).pack == 2

        assert Union(*self.TEST_MEMBERS).members == self.TEST_MEMBERS

    def test_list_equality(self):
        assert Struct(*self.TEST_MEMBERS, pack=2) == {
            "members": [("a", Type("int"), None), ("b", Type("char", "*"), None)],
            "pack": 2,
        }
        assert issubclass(Struct, dict)

        assert Union(*self.TEST_MEMBERS)["members"] == self.TEST_MEMBERS

    def test_repr(self):
        assert repr(Struct()) == "Struct()"
        assert repr(Struct(*self.TEST_MEMBERS, pack=2)) == (
            "Struct("
            + repr(self.TEST_MEMBERS[0])
            + ", "
            + repr(self.TEST_MEMBERS[1])
            + ", pack=2)"
        )
        assert repr(Union()) == "Union()"


class TestEnum(object):
    def test_dict_equality(self):
        assert Enum(a=1, b=2) == {"a": 1, "b": 2}
        assert issubclass(Enum, dict)

    def test_repr(self):
        assert repr(Enum(a=1, b=2)) == "Enum(a=1, b=2)"


class TestFileHandling(object):
    """Test parser basic file operations."""

    h_dir = os.path.join(H_DIRECTORY, "file_handling")

    def setup_method(self):
        self.parser = CParser(process_all=False)

    def test_init(self):
        parser = CParser(os.path.join(self.h_dir, "replace.h"))
        assert parser.files is not None

    def test_find_file(self):
        saved_headers = pyclibrary.utils.HEADER_DIRS
        try:
            pyclibrary.utils.add_header_locations([self.h_dir])
            assert self.h_dir in pyclibrary.utils.HEADER_DIRS
            assert self.parser.find_headers(["replace.h"]) == [
                os.path.join(self.h_dir, "replace.h")
            ]
        finally:
            pyclibrary.utils.HEADER_DIRS = saved_headers

        abs_hdr_path = os.path.join(self.h_dir, "replace.h")
        assert self.parser.find_headers([abs_hdr_path]) == [abs_hdr_path]
        abs_hdr_path2 = os.path.join(self.h_dir, "c_comments.h")
        assert len(self.parser.find_headers([abs_hdr_path, abs_hdr_path2])) == 2

    def test_load_file(self):
        path = os.path.join(self.h_dir, "replace.h")
        assert self.parser.load_file(path)
        assert self.parser.files[path] is not None
        assert self.parser.file_order == [path]
        assert self.parser.init_opts["replace"]["replace.h"] is None
        assert self.parser.init_opts["files"] == ["replace.h"]

    def test_load_file_and_replace(self):
        path = os.path.join(self.h_dir, "replace.h")
        rep = {"{placeholder}": "1", "placeholder2": "2"}
        assert self.parser.load_file(path, rep)

        lines = self.parser.files[path].split("\n")
        assert lines[3] == "# define MACRO 1"
        assert lines[6] == "    # define MACRO2 2"

        lines[3] = "# define MACRO {placeholder}"
        lines[6] = "    # define MACRO2 placeholder2"
        with open(path) as f:
            compare_lines(lines, f.readlines())

        assert self.parser.file_order == [path]
        assert self.parser.init_opts["replace"]["replace.h"] == rep
        assert self.parser.init_opts["files"] == ["replace.h"]

    def test_load_non_existing_file(self):
        path = os.path.join(self.h_dir, "no.h")
        assert not self.parser.load_file(path)
        assert self.parser.files[path] is None

    def test_removing_c_comments(self):
        path = os.path.join(self.h_dir, "c_comments.h")
        self.parser.load_file(path)
        self.parser.remove_comments(path)
        with open(os.path.join(self.h_dir, "c_comments_removed.h"), "r") as f:
            compare_lines(self.parser.files[path].split("\n"), f.readlines())

    def test_removing_cpp_comments(self):
        path = os.path.join(self.h_dir, "cpp_comments.h")
        self.parser.load_file(path)
        self.parser.remove_comments(path)
        with open(os.path.join(self.h_dir, "cpp_comments_removed.h"), "r") as f:
            compare_lines(self.parser.files[path].split("\n"), f.readlines())


class TestPreprocessing(object):
    """Test preprocessing."""

    h_dir = os.path.join(H_DIRECTORY, "macros")

    def setup_method(self):
        self.parser = CParser(process_all=False)

    def test_values(self):
        path = os.path.join(self.h_dir, "macro_values.h")
        self.parser.load_file(path)
        self.parser.remove_comments(path)
        self.parser.preprocess(path)

        macros = self.parser.defs["macros"]
        values = self.parser.defs["values"]

        assert "M" in macros and macros["M"] == ""
        assert "N" in macros and macros["N"] == "n" and values["N"] is None

        # Decimal integer
        assert (
            "MACRO_D1" in macros
            and macros["MACRO_D1"] == "1"
            and values["MACRO_D1"] == 1
        )
        assert (
            "MACRO_D2" in macros
            and macros["MACRO_D2"] == "-2U"
            and values["MACRO_D2"] == -2
        )
        assert (
            "MACRO_D3" in macros
            and macros["MACRO_D3"] == "+ 3UL"
            and values["MACRO_D3"] == 3
        )

        # Bit shifted decimal integer
        assert (
            "MACRO_SD1" in macros
            and macros["MACRO_SD1"] == "(1 << 1)"
            and values["MACRO_SD1"] == 2
        )
        assert (
            "MACRO_SD2" in macros
            and macros["MACRO_SD2"] == "(2U << 2)"
            and values["MACRO_SD2"] == 8
        )
        assert (
            "MACRO_SD3" in macros
            and macros["MACRO_SD3"] == "(3UL << 3)"
            and values["MACRO_SD3"] == 24
        )

        # Hexadecimal integer
        assert (
            "MACRO_H1" in macros
            and macros["MACRO_H1"] == "+0x000000"
            and values["MACRO_H1"] == 0
        )
        assert (
            "MACRO_H2" in macros
            and macros["MACRO_H2"] == "- 0x000001U"
            and values["MACRO_H2"] == -1
        )
        assert (
            "MACRO_H3" in macros
            and macros["MACRO_H3"] == "0X000002UL"
            and values["MACRO_H3"] == 2
        )

        # Bit shifted hexadecimal integer
        assert (
            "MACRO_SH1" in macros
            and macros["MACRO_SH1"] == "(0x000000 << 1)"
            and values["MACRO_SH1"] == 0
        )
        assert (
            "MACRO_SH2" in macros
            and macros["MACRO_SH2"] == "(0x000001U << 2)"
            and values["MACRO_SH2"] == 4
        )
        assert (
            "MACRO_H3" in macros
            and macros["MACRO_SH3"] == "(0X000002UL << 3)"
            and values["MACRO_SH3"] == 16
        )

        # Floating point value
        assert (
            "MACRO_F1" in macros
            and macros["MACRO_F1"] == "1.0"
            and values["MACRO_F1"] == 1.0
        )
        assert (
            "MACRO_F2" in macros
            and macros["MACRO_F2"] == "1.1e1"
            and values["MACRO_F2"] == 11.0
        )
        assert (
            "MACRO_F3" in macros
            and macros["MACRO_F3"] == "-1.1E-1"
            and values["MACRO_F3"] == -0.11
        )

        # String macro
        assert (
            "MACRO_S" in macros
            and macros["MACRO_S"] == '"test"'
            and values["MACRO_S"] == "test"
        )

        # Nested macros
        assert "NESTED" in macros and macros["NESTED"] == "1" and values["NESTED"] == 1
        assert (
            "NESTED2" in macros and macros["NESTED2"] == "1" and values["NESTED2"] == 1
        )
        assert (
            "MACRO_N" in macros
            and macros["MACRO_N"] == "1 + 2"
            and values["MACRO_N"] == 3
        )

        # Muliline macro
        assert "MACRO_ML" in macros and values["MACRO_ML"] == 2

    def test_conditionals(self):
        path = os.path.join(self.h_dir, "macro_conditionals.h")
        self.parser.load_file(path)
        self.parser.remove_comments(path)
        self.parser.preprocess(path)
        self.parser.parse_defs(path)

        macros = self.parser.defs["macros"]
        stream = self.parser.files[path]

        # Test if defined conditional
        assert "DEFINE_IF" in macros
        assert "  int DECLARE_IF;\n" in stream
        assert "NO_DEFINE_IF" not in macros
        assert "  int NO_DECLARE_IF;\n" not in stream

        # Test ifdef conditional
        assert "DEFINE_IFDEF" in macros
        assert "  int DECLARE_IFDEF;\n" in stream
        assert "NO_DEFINE_IFDEF" not in macros
        assert "  int NO_DECLARE_IFDEF;\n" not in stream

        # Test if !defined
        assert "DEFINE_IFN" in macros
        assert "  int DECLARE_IFN;\n" in stream
        assert "NO_DEFINE_IFN" not in macros
        assert "  int NO_DECLARE_IFN;\n" not in stream

        # Test ifndef
        assert "DEFINE_IFNDEF" in macros
        assert "  int DECLARE_IFNDEF;\n" in stream
        assert "NO_DEFINE_IFNDEF" not in macros
        assert "  int NO_DECLARE_IFNDEF;\n" not in stream

        # Test elif
        assert "DEFINE_ELIF" in macros
        assert "  int DECLARE_ELIF;\n" in stream
        assert "NO_DEFINE_ELIF" not in macros
        assert "  int NO_DECLARE_ELIF;\n" not in stream

        # Test else
        assert "DEFINE_ELSE" in macros
        assert "  int DECLARE_ELSE;\n" in stream
        assert "NO_DEFINE_ELSE" not in macros
        assert "  int NO_DECLARE_ELSE;\n" not in stream

        # Test nested
        assert "DEFINE_N1" in macros
        assert "  int DECLARE_N1;\n" in stream
        assert "NO_DEFINE_N2" not in macros
        assert "DEFINE_N2" not in macros

        assert "DEFINE_N3" in macros
        assert "NO_DEFINE_N3" not in macros
        assert "  int NO_DECLARE_N3;\n" not in stream

        # Test logical
        assert "DEFINE_LOG" in macros
        assert "  int DECLARE_LOG;\n" in stream
        assert "NO_DEFINE_LOG" not in macros
        assert "NO_DEFINE_LOG" not in macros

        # Test undef
        assert "DEFINE_UNDEF" in macros
        assert "UNDEF" not in macros

    def test_macro_function(self):
        path = os.path.join(self.h_dir, "macro_functions.h")
        self.parser.load_file(path)
        self.parser.remove_comments(path)
        self.parser.preprocess(path)
        self.parser.parse_defs(path)

        values = self.parser.defs["values"]
        fnmacros = self.parser.defs["fnmacros"]
        stream = self.parser.files[path]

        # Test macro declaration.
        assert "CARRE" in fnmacros
        assert "int carre = 2*2;" in stream

        assert "int __declspec(dllexport) function2()" in stream
        assert "__declspec(dllexport) int function3()" in stream
        assert "__declspec(dllexport) int * function4()" in stream

        # Test defining a macro function as an alias for another one.
        assert "MAKEINTRESOURCEA" in fnmacros
        assert "MAKEINTRESOURCEW" in fnmacros
        assert "MAKEINTRESOURCE" in fnmacros
        assert fnmacros["MAKEINTRESOURCE"] == fnmacros["MAKEINTRESOURCEA"]
        assert "int x = ((LPSTR)((ULONG_PTR)((WORD)(4))))"

        # Test using a macro value in a macro function call
        assert "BIT" in values and values["BIT"] == 1
        assert "((y) |= (0x01))" in stream

        # Test defining a macro function calling other macros (values and
        # functions)
        assert "SETBITS" in fnmacros
        assert "int z1, z2 = (((1) |= (0x01)), ((2) |= (0x01)));" in stream

        # Test defining a macro function calling nested macro functions
        assert "SETBIT_AUTO" in fnmacros
        assert "int z3 = ((((3) |= (0x01)), ((3) |= (0x01))));" in stream

    def test_pragmas(self):
        path = os.path.join(self.h_dir, "pragmas.h")
        self.parser.load_file(path)
        self.parser.remove_comments(path)
        self.parser.preprocess(path)
        self.parser.parse_defs(path)

        stream = self.parser.files[path]
        packings = self.parser.pack_list[path]

        # Check all pragmas instructions have been removed.
        assert stream.strip() == ""

        assert packings[1][1] is None
        assert packings[2][1] == 4
        assert packings[3][1] == 16
        assert packings[4][1] is None
        assert packings[5][1] is None
        assert packings[6][1] == 4
        assert packings[7][1] == 16
        assert packings[8][1] is None


class TestParsing(object):
    """Test parsing."""

    h_dir = H_DIRECTORY

    def setup_method(self):
        self.parser = CParser(process_all=False)

    def test_variables(self):
        path = os.path.join(self.h_dir, "variables.h")
        self.parser.load_file(path)
        self.parser.process_all()

        variables = self.parser.defs["variables"]

        # Integers
        assert "short1" in variables and variables["short1"] == (
            1,
            Type("signed short"),
        )
        assert "short_int" in variables and variables["short_int"] == (
            1,
            Type("short int"),
        )
        assert "short_un" in variables and variables["short_un"] == (
            1,
            Type("unsigned short"),
        )
        assert "short_int_un" in variables and variables["short_int_un"] == (
            1,
            Type("unsigned short int"),
        )
        assert "int1" in variables and variables["int1"] == (1, Type("int"))
        assert "un" in variables and variables["un"] == (1, Type("unsigned"))
        assert "int_un" in variables and variables["int_un"] == (
            1,
            Type("unsigned int"),
        )
        assert "long1" in variables and variables["long1"] == (1, Type("long"))
        assert "long_int" in variables and variables["long_int"] == (
            1,
            Type("long int"),
        )
        assert "long_un" in variables and variables["long_un"] == (
            1,
            Type("unsigned long"),
        )
        assert "long_int_un" in variables and variables["long_int_un"] == (
            1,
            Type("unsigned long int"),
        )
        if sys.platform == "win32":
            assert "int64" in variables and variables["int64"] == (1, Type("__int64"))
            assert "int64_un" in variables and variables["int64_un"] == (
                1,
                Type("unsigned __int64"),
            )
        assert "long_long" in variables and variables["long_long"] == (
            1,
            Type("long long"),
        )
        assert "long_long_int" in variables and variables["long_long_int"] == (
            1,
            Type("long long int"),
        )
        assert "long_long_un" in variables and variables["long_long_un"] == (
            1,
            Type("unsigned long long"),
        )
        assert "long_long_int_un" in variables and variables["long_long_int_un"] == (
            1,
            Type("unsigned long long int"),
        )

        # stddef integers
        assert "size" in variables and variables["size"] == (
            1,
            Type("size_t"),
        )
        assert "ssize" in variables and variables["ssize"] == (
            1,
            Type("ssize_t"),
        )

        # C99 integers
        for i in (8, 16, 32, 64):
            assert "i%d" % i in variables and variables["i%d" % i] == (
                1,
                Type("int%d_t" % i),
            )
            assert "u%d" % i in variables and variables["u%d" % i] == (
                1,
                Type("uint%d_t" % i),
            )

        # Floating point number
        assert "fl" in variables and variables["fl"] == (1.0, Type("float"))
        assert "db" in variables and variables["db"] == (0.1, Type("double"))
        assert "dbl" in variables and variables["dbl"] == (-10.0, Type("long double"))

        # Const and static modif
        assert "int_const" in variables and variables["int_const"] == (
            4,
            Type("int", type_quals=(("const",),)),
        )
        assert "int_stat" in variables and variables["int_stat"] == (4, Type("int"))
        assert "int_con_stat" in variables and variables["int_con_stat"] == (
            4,
            Type("int", type_quals=(("const",),)),
        )
        assert "int_extern" in variables and variables["int_extern"] == (4, Type("int"))

        # String
        assert "str1" in variables and variables["str1"] == (
            "normal string",
            Type("char", "*"),
        )
        assert "str2" in variables and variables["str2"] == (
            "string with macro: INT",
            Type("char", "*", "*"),
        )
        assert "str3" in variables and variables["str3"] == (
            "string with comment: /*comment inside string*/",
            Type("char", "*", type_quals=(("const",), ("const",))),
        )
        assert "str4" in variables and variables["str4"] == (
            "string with define #define MACRO5 macro5_in_string ",
            Type("char", "*"),
        )
        assert "str5" in variables and variables["str5"] == (
            'string with "escaped quotes" ',
            Type("char", "*"),
        )

        # Test complex evaluation
        assert "x1" in variables and variables["x1"] == (1.0, Type("float"))

        # Test type casting handling.
        assert "x2" in variables and variables["x2"] == (88342528, Type("int"))

        # Test array handling
        assert "array" in variables and variables["array"] == (
            [1, 3141500.0],
            Type("float", [2]),
        )
        # assert ('array2d' in variables and
        #         variables['array2d'] == ([[1, 2, 3], [4, 5, 6]], Type('float', [2, 3])))
        assert "intJunk" in variables and variables["intJunk"] == (
            None,
            Type(
                "int",
                "*",
                "*",
                "*",
                [4],
                type_quals=(("const",), ("const",), (), (), ()),
            ),
        )

        # time_t
        if sys.version_info >= (3, 12):
            assert "time" in variables and variables["time"] == (
                1,
                Type("time_t"),
            )

        # test type qualifiers
        assert variables.get("typeQualedIntPtrPtr") == (
            None,
            Type("int", "*", "*", type_quals=(("const",), ("volatile",), ())),
        )
        assert variables.get("typeQualedIntPtr") == (
            None,
            Type(
                "int",
                "*",
                type_quals=(
                    (
                        "const",
                        "volatile",
                    ),
                    (),
                ),
            ),
        )

        # test type definition precedence
        assert variables.get("prec_ptr_of_arr") == (None, Type("int", [1], "*"))
        assert variables.get("prec_arr_of_ptr") == (None, Type("int", "*", [1]))
        assert variables.get("prec_arr_of_ptr2") == (None, Type("int", "*", [1]))

    # No structure, no unions, no enum
    def test_typedef(self):
        path = os.path.join(self.h_dir, "typedefs.h")
        self.parser.load_file(path)
        self.parser.process_all()

        types = self.parser.defs["types"]
        variables = self.parser.defs["variables"]

        # Test defining types from base types.
        assert "typeChar" in types and types["typeChar"] == Type("char", "*", "*")
        assert "typeInt" in types and types["typeInt"] == Type("int")
        assert "typeIntPtr" in types and types["typeIntPtr"] == Type("int", "*")
        assert "typeIntArr" in types and types["typeIntArr"] == Type("int", [10])
        assert "typeIntDArr" in types and types["typeIntDArr"] == Type("int", [5], [6])
        assert "typeTypeInt" in types and types["typeTypeInt"] == Type("typeInt")
        assert not self.parser.is_fund_type("typeTypeInt")
        assert self.parser.eval_type(["typeTypeInt"]) == Type("int")
        assert "ULONG" in types and types["ULONG"] == Type("unsigned long")

        # Test annotated types
        assert "voidpc" in types and types["voidpc"] == Type(
            "void", "*", type_quals=(("const",), ())
        )
        assert "charf" in types and types["charf"] == Type(
            "char", type_quals=(("far",),)
        )

        # Test using custom type.
        assert "ttip5" in variables and variables["ttip5"] == (
            None,
            Type("typeTypeInt", "*", [5]),
        )

        # Handling undefined types
        assert "SomeOtherType" in types and types["SomeOtherType"] == Type("someType")
        assert "x" in variables and variables["x"] == (None, Type("undefined"))
        assert not self.parser.is_fund_type("SomeOtherType")
        with pytest.raises(Exception):
            self.parser.eval_type(Type("undefined"))

        # Testing recursive defs
        assert "recType1" in types
        assert "recType2" in types
        assert "recType3" in types
        with pytest.raises(Exception):
            self.parser.eval_type(Type("recType3"))

    def test_enums(self):
        path = os.path.join(self.h_dir, "enums.h")
        self.parser.load_file(path)
        self.parser.process_all()

        enums = self.parser.defs["enums"]
        types = self.parser.defs["types"]
        variables = self.parser.defs["variables"]
        functions = self.parser.defs["functions"]
        print(self.parser.defs["values"])
        assert "enum_name" in enums and "enum enum_name" in types
        assert enums["enum_name"] == {"enum1": 129, "enum2": 6, "enum3": 7, "enum4": 8}
        assert types["enum enum_name"] == Type(
            "enum",
            "enum_name",
        )
        assert "enum_inst" in variables and variables["enum_inst"] == (
            None,
            Type(
                "enum enum_name",
            ),
        )

        assert "anon_enum0" in enums
        assert "anon_enum1" in enums
        assert "no_name_enum_typeddef" in types

        assert "function_taking_enum" in functions
        assert functions["function_taking_enum"] == Type(
            Type("void"), (("e", Type("enum enum_name"), None),)
        )

    def test_struct(self):
        path = os.path.join(self.h_dir, "structs.h")
        self.parser.load_file(path)
        self.parser.process_all()

        structs = self.parser.defs["structs"]
        types = self.parser.defs["types"]
        variables = self.parser.defs["variables"]

        # Test creating a structure using only base types.
        assert "struct_name" in structs and "struct struct_name" in types
        assert structs["struct_name"] == Struct(
            ("x", Type("int"), 1),
            ("y", Type("type_type_int"), None, 2),
            ("str", Type("char", [10]), None),
        )
        assert "struct_inst" in variables and variables["struct_inst"] == (
            None,
            Type("struct struct_name"),
        )

        # Test creating a structure using only base types.
        assert "struct_arr" in structs and "struct struct_arr" in types
        assert structs["struct_arr"] == Struct(("str", Type("char", [10], [20]), None))
        assert "struct_inst" in variables and variables["struct_inst"] == (
            None,
            Type("struct struct_name"),
        )

        # Test creating a pointer type from a structure.
        assert "struct_name_ptr" in types and types["struct_name_ptr"] == Type(
            "struct struct_name", "*"
        )

        assert "struct_name2_ptr" in types and types["struct_name2_ptr"] == Type(
            "struct anon_struct0", "*"
        )

        # Test declaring a recursive structure.
        assert "recursive_struct" in structs and "struct recursive_struct" in types
        assert structs["recursive_struct"] == Struct(
            ("next", Type("struct recursive_struct", "*"), None)
        )

        # Test declaring near and far pointers.
        assert "tagWNDCLASSEXA" in structs
        assert "NPWNDCLASSEXA" in types and (
            types["NPWNDCLASSEXA"]
            == Type("struct tagWNDCLASSEXA", "*", type_quals=(("near",), ()))
        )

        # Test altering the packing of a structure.
        assert "struct_name_p" in structs and "struct struct_name_p" in types
        assert structs["struct_name_p"] == Struct(
            ("x", Type("int"), None),
            ("y", Type("type_type_int"), None),
            ("str", Type("char", [10]), "brace }  \0"),
            pack=16,
        )

        # Test nested structures
        NESTED_STRUCT_ENUM_0 = self.parser.defs["enums"]["root_nested_enum"][
            "NESTED_STRUCT_ENUM_0"
        ]
        NESTED_STRUCT_ENUM_1 = self.parser.defs["enums"]["root_nested_enum"][
            "NESTED_STRUCT_ENUM_1"
        ]
        NESTED_STRUCT_ENUM_2 = self.parser.defs["enums"]["root_nested_enum"][
            "NESTED_STRUCT_ENUM_2"
        ]
        assert NESTED_STRUCT_ENUM_0 == 0
        assert NESTED_STRUCT_ENUM_1 == 1
        assert NESTED_STRUCT_ENUM_2 == 2

        assert (
            "root_nested_structure" in structs
            and "struct root_nested_structure" in types
        )
        assert structs["root_nested_structure"] == Struct(
            ("x", Type("struct leaf1_nested_structure", [NESTED_STRUCT_ENUM_2]), None),
            ("y", Type("root_nested_enum_type"), None),
            ("z", Type("struct leaf2_nested_structure"), None),
            pack=16,
        )

    def test_unions(self):
        path = os.path.join(self.h_dir, "unions.h")
        self.parser.load_file(path)
        self.parser.process_all()

        unions = self.parser.defs["unions"]
        structs = self.parser.defs["structs"]
        types = self.parser.defs["types"]
        variables = self.parser.defs["variables"]

        # Test declaring an union.
        assert "union_name" in unions and "union union_name" in types
        assert unions["union_name"] == Union(
            ("x", Type("int"), 1), ("y", Type("int"), None), pack=None
        )
        assert "union_name_ptr" in types and types["union_name_ptr"] == Type(
            "union union_name", "*"
        )

        # Test defining an unnamed union
        assert "no_name_union_inst" in variables and variables[
            "no_name_union_inst"
        ] == (None, Type("union anon_union0"))

        # Test defining a structure using an unnamed union internally.
        assert "tagRID_DEVICE_INFO" in structs and structs[
            "tagRID_DEVICE_INFO"
        ] == Struct(
            ("cbSize", Type("DWORD"), None),
            ("dwType", Type("DWORD"), None),
            (None, Type("union anon_union1"), None),
        )

        assert "RID_DEVICE_INFO" in types and types["RID_DEVICE_INFO"] == Type(
            "struct tagRID_DEVICE_INFO"
        )
        assert "PRID_DEVICE_INFO" in types and types["PRID_DEVICE_INFO"] == Type(
            "struct tagRID_DEVICE_INFO", "*"
        )
        assert "LPRID_DEVICE_INFO" in types and (
            types["LPRID_DEVICE_INFO"] == Type("struct tagRID_DEVICE_INFO", "*")
        )

    def test_functions(self):
        path = os.path.join(self.h_dir, "functions.h")
        self.parser.load_file(path)
        self.parser.process_all()

        functions = self.parser.defs["functions"]
        variables = self.parser.defs["variables"]

        assert functions.get("f") == Type(
            Type("void"), ((None, Type("int"), None), (None, Type("int"), None))
        )
        assert functions["g"] == Type(
            Type("int"),
            (("ch", Type("char", "*"), None), ("str", Type("char", "*", "*"), None)),
        )
        assert variables.get("fnPtr") == (
            None,
            Type("int", ((None, Type("char"), None), (None, Type("float"), None)), "*"),
        )
        assert functions.get("function1") == Type(
            Type("int", "__stdcall", type_quals=((), None)), ()
        )

        assert functions.get("function2") == Type(Type("int"), ())

        assert "externFunc" in functions

        ptyp = Type("int", "*", "*", type_quals=(("volatile",), ("const",), ()))
        assert functions.get("typeQualedFunc") == Type(
            Type("int"), ((None, ptyp, None),)
        )
