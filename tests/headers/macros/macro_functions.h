/* This file is used to test the preprocessing of macro functions*/

// Test macro function definition
#define CARRE(a) a*a
int carre = CARRE(2);

#define EXPORT(x) x __declspec(dllexport)
EXPORT(int) function2();

#define EXPORT(x) __declspec(dllexport) x
EXPORT(int) function3();

#define EXPORT(x) __declspec(dllexport) x
EXPORT(int *) function4();

// Test defining a macro function as an alias for another one.
#define MAKEINTRESOURCEA(i) ((LPSTR)((ULONG_PTR)((WORD)(i))))
#define MAKEINTRESOURCEW(i) ((LPWSTR)((ULONG_PTR)((WORD)(i))))

#ifdef UNICODE
  #define MAKEINTRESOURCE  MAKEINTRESOURCEW
#else
  #define MAKEINTRESOURCE  MAKEINTRESOURCEA
#endif // !UNICODE
int x = MAKEINTRESOURCE(4);

// Test using a macro value in a macro function call
#define BIT 0x01
#define SETBIT(x, b)   ((x) |= (b))
int y = 0;
SETBIT(y, BIT);

// Test defining a macro function calling other macros (values and functions)
#define SETBITS(x, y) (SETBIT(x, BIT), SETBIT(y, BIT))
int z1, z2 = SETBITS(1, 2); // This is incorrect but can be preprocessed.

// Test defining a macro function calling nested macro functions
#define SETBIT_AUTO(x) (SETBITS(x, x))
int z3 = SETBIT_AUTO(3);
