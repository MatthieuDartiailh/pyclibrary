/* Test header for parsing enumerations. */

#define VALUE 128

enum enum_name
{
    enum1= (VALUE | 1),
    enum2=6,
    enum3,
    enum4,
}  enum_inst;


enum {
    x = 0,
    y
} no_name_enum_inst;


typedef enum
{
    typedef_enum1 = 1,
    typedef_enum2
} no_name_enum_typeddef;

void function_taking_enum(enum enum_name e);
