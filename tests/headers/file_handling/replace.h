// This header file is used to test the parser capability to replace arbitrary
// string when loading a file.

# define MACRO {placeholder}

# ifdef MACRO:
    # define MACRO2 placeholder2
# endifdef