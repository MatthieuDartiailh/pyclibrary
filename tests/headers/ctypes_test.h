/********************************************************************
 Hand written header file for the _ctype_test library used in testing
 ********************************************************************/

#if defined(MS_WIN32) || defined(__CYGWIN__)
#define EXPORT(x) __declspec(dllexport) x
#else
#define EXPORT(x) x
#endif


// Test basic global variable and basic function call.

EXPORT(int) an_integer = 42;

EXPORT(int) get_an_integer(void)
{
    return an_integer;
}

// Test function calls returning type that needs to be correctly interpreted
// to make sense (if restype is wrong won't work.
EXPORT(char *) my_strdup(char *src);

// Bunch of structure to test structure creation and access to global variables
// made of complex structures.

typedef struct {
    char names[10][20];
} T;

typedef struct {
    char *name;
    char *value;
} SPAM;

typedef struct {
    char *name;
    int num_spams;
    SPAM *spams;
} EGG;

SPAM my_spams[2] = {
    { "name1", "value1" },
    { "name2", "value2" },
};

EGG my_eggs[1] = {
    { "first egg", 1, my_spams }
};


// Functions used to test passing no pointer and getting the right object out.

EXPORT(int) getSPAMANDEGGS(EGG **eggs)
{
    *eggs = my_eggs;
    return 1;
}

typedef struct tagpoint {
    int x;
    int y;
} point;

EXPORT(int) _testfunc_byval(point in, point *pout)
{
    if (pout) {
        pout->x = in.x;
        pout->y = in.y;
    }
    return in.x + in.y;
}


// Bit fields manipulations.

struct BITS {
    int A: 1, B:2, C:3, D:4, E: 5, F: 6, G: 7, H: 8, I: 9;
    short M: 1, N: 2, O: 3, P: 4, Q: 5, R: 6, S: 7;
};

EXPORT(void) set_bitfields(struct BITS *bits, char name, int value)
{
    switch (name) {
    case 'A': bits->A = value; break;
    case 'B': bits->B = value; break;
    case 'C': bits->C = value; break;
    case 'D': bits->D = value; break;
    case 'E': bits->E = value; break;
    case 'F': bits->F = value; break;
    case 'G': bits->G = value; break;
    case 'H': bits->H = value; break;
    case 'I': bits->I = value; break;

    case 'M': bits->M = value; break;
    case 'N': bits->N = value; break;
    case 'O': bits->O = value; break;
    case 'P': bits->P = value; break;
    case 'Q': bits->Q = value; break;
    case 'R': bits->R = value; break;
    case 'S': bits->S = value; break;
    }
}

EXPORT(int) unpack_bitfields(struct BITS *bits, char name)
{
    switch (name) {
    case 'A': return bits->A;
    case 'B': return bits->B;
    case 'C': return bits->C;
    case 'D': return bits->D;
    case 'E': return bits->E;
    case 'F': return bits->F;
    case 'G': return bits->G;
    case 'H': return bits->H;
    case 'I': return bits->I;

    case 'M': return bits->M;
    case 'N': return bits->N;
    case 'O': return bits->O;
    case 'P': return bits->P;
    case 'Q': return bits->Q;
    case 'R': return bits->R;
    case 'S': return bits->S;
    }
    return 0;
}
