/* Header file to test the parsing of typedef based on simple type, enum,
struct and union will be treated later. */

// Standard type defintion
typedef char **typeChar;
typedef int typeInt, *typeIntPtr, typeIntArr[10], typeIntDArr[5][6];
typedef typeInt typeTypeInt;
typedef unsigned long ULONG;

// Typedef using type anotations.
typedef void const *voidpc;
typedef char far charf;

// test using newly defined type.
typeTypeInt *ttip5[5];

// Handling of undefined types.
typedef someType SomeOtherType;
undefined x;

// Recursive type definitions
typedef recType1 recType2;
typedef recType2 recType3;
typedef recType3 recType1;
