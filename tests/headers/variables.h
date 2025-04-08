/* Test the parsing of variables of standard types in a header*/

#define INT 1
#define SQUARE(i) i*i
// Test defining standard variables.
// Integers
signed short short1 = 1;
short int short_int = INT;
unsigned short short_un = 1;
unsigned short int short_int_un = 1;
int int1 = 0x1;
unsigned un = 1;
unsigned int int_un = +1;
long long1 = 1;
long int long_int = 1;
unsigned long long_un = 1;
unsigned long int long_int_un = 1;
__int64 int64 = 1;
unsigned __int64 int64_un = 1;
long long long_long = 1;
long long int long_long_int = 1;
unsigned long long long_long_un = 1;
unsigned long long int long_long_int_un = 1;

// stddef integers
size_t size = 1;
ssize_t ssize = 1;

// C99 integers
int8_t i8 = 1;
int16_t i16 = 1;
int32_t i32 = 1;
int64_t i64 = 1;
uint8_t u8 = 1;
uint16_t u16 = 1;
uint32_t u32 = 1;
uint64_t u64 = 1;

// Floating points numbers
float fl = + 1.0;
double db = 1e-1;
long double dbl = - 1E1;

// Static and const modifiers
const int int_const = SQUARE(2);
static int int_stat = SQUARE(2);
static const int int_con_stat = SQUARE(2);
extern int int_extern = SQUARE(2);

// String
char* str1 = "normal string";
char** str2 = "string with macro: INT";
static const char* const str3 = "string with comment: /*comment inside string*/";
char* str4 = "string with define #define MACRO5 macro5_in_string ";
char* str5 = "string with \"escaped quotes\" ";

// Test complex evaluation.
float x1 = (5 + 3 * 0x1) / 8.0;

// Test type casting handling.
int x2 = (typeCast)0x544 <<16;

// Test array
float array[2] = {0x1, 3.1415e6};
static const int * const (**intJunk[4]);

// time_t
time_t time = 1;

const int * volatile * typeQualedIntPtrPtr, volatile * typeQualedIntPtr;

// Test type definition precedence
int (*prec_ptr_of_arr)[1], *(prec_arr_of_ptr[1]), *prec_arr_of_ptr2[1];
