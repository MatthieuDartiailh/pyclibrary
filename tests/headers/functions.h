/* Header testing function definitions parsing. */

//Defining a standard function.
void f(int, int);

// Defining a function with its implementation following
inline int g(char *ch, char **str)
{
     JUNK
     switch (str){
        case 'r': return 0;
     }
     int localVariable = 1;
}

// Defining a function pointer.
int(*fnPtr)(char, float);


// Adding dllexport and stdcall annotation to a function.
extern int __declspec(dllexport) __stdcall function1();
__declspec(noreturn) void __stdcall pre_declspec_func(void);

#define EXPORT(x) x __declspec(dllexport)

EXPORT(int) function2();

extern int externFunc(void);

//define typequals in abstract typedef
int typeQualedFunc(int volatile * const *);

void array_param_func(int arr_params[]);
