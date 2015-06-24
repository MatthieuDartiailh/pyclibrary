/* Test header for parsing struct. */

typedef int type_int;
typedef type_int type_type_int;

// Test creating a structure using only base types.
// Test for default values, array handling and bit length specifications.
struct struct_name
{
  int x = 1;
  type_type_int y:2;
  char str[10]; /* commented brace } */
} struct_inst;

// Test creating a pointer type from a structure.
typedef struct struct_name *struct_name_ptr;

typedef struct {
    int x;
    int y;
} *struct_name2_ptr;

// Test declaring a recursive structure.
struct recursive_struct {
    struct recursive_struct *next;
};

// Test declaring near and far pointers.
typedef struct tagWNDCLASSEXA {
    int         cbClsExtra;
    int         cbWndExtra;
} WNDCLASSEXA, *PWNDCLASSEXA, __allowed("N") *NPWNDCLASSEXA, __allowed("L") *LPWNDCLASSEXA;

// Test altering the packing of a structure.
#pragma pack(push, 16)
struct struct_name_p
{
  int x; type_type_int y;
  char str[10] = "brace }  \0"; /* commented brace } */
};

#pragma pack(pop)
struct default_packsize
{
    int x;
} ;

struct unnamed_struct {
    struct struct_name;
} ;

struct {
    long x;
    struct { int y; } ;
} anonymous_struct_inst;

const struct typequals {
    int x;
} volatile typequals_var;
