/* Test header for parsing enumerations. */

enum enum_name
{
    enum1=2,
    enum2=6,
    enum3,
    enum4,
}  enum_inst;

enum enum_name enum_inst2;


enum {
    x = 0,
    y
} no_name_enum_inst;

enum {
    x = 0,
    y
} no_name_enum_inst2;
