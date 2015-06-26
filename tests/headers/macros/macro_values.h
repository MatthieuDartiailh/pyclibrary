/* This is file is used to test the processing of macro values. */

#define M
#define N n

// Decimal values
#define MACRO_D1 1
#define MACRO_D2 -2U
#define MACRO_D3 + 3UL

// Bit shifted decimal values
#define MACRO_SD1 (1 << 1)
#define MACRO_SD2 (2U << 2)
#define MACRO_SD3 (3UL << 3)

// Hexadecimal values
#define MACRO_H1 +0x000000
#define MACRO_H2 - 0x000001U
#define MACRO_H3 0X000002UL

// Bit shifted hexadecimal values
#define MACRO_SH1 (0x000000 << 1)
#define MACRO_SH2 (0x000001U << 2)
#define MACRO_SH3 (0X000002UL << 3)

// Floating values
#define MACRO_F1 1.0
#define MACRO_F2 1.1e1
#define MACRO_F3 -1.1E-1

// String macro
#define MACRO_S "test"

// Nested macro
#define MACRO 1
#define MACRO2 2
#define NESTED MACRO
#define NESTED2 NESTED
#define MACRO_N MACRO + MACRO2

// Multiline macro
#define MACRO_ML MACRO\
                  *MACRO2
