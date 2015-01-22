/* Header testing function definitions parsing. */

//Defining a standard function.
void f(int, int);
inline int g(char *ch, char **str);

// Defining a function pointer.
int(*fnPtr)(char, float);

// Adding dllexport and stdcall annotation to a function.
int __declspec(dllexport) __stdcall function1();
