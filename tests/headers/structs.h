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


// Test creating a structure using only base types.
// Test for default values, array handling and bit length specifications.
struct struct_arr
{
  char str[10][20]; /* commented brace } */
} struct_arr;

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
} WNDCLASSEXA, *PWNDCLASSEXA, near *NPWNDCLASSEXA, far *LPWNDCLASSEXA;

// Test altering the packing of a structure.
#pragma pack(16)
struct struct_name_p
{
  int x; type_type_int y;
  char str[10] = "brace }  \0"; /* commented brace } */
};

// Test a nested structure

typedef enum root_nested_enum
{
  NESTED_STRUCT_ENUM_0,
  NESTED_STRUCT_ENUM_1,
  NESTED_STRUCT_ENUM_2
} root_nested_enum_type;

struct root_nested_structure
{
  struct leaf1_nested_structure{
    char x;
  } x[NESTED_STRUCT_ENUM_2];
  root_nested_enum_type y;
  struct leaf2_nested_structure{
    char x;        
  } z;
};