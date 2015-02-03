/********************************************************************
 Hand written header file for the _ctype_test library used in testing
 ********************************************************************/


#if defined(MS_WIN32) || defined(__CYGWIN__)
#define EXPORT(x) __declspec(dllexport) x
#else
#define EXPORT(x) x
#endif

EXPORT(void)testfunc_array(int values[4])
{
    printf("testfunc_array %d %d %d %d\n",
           values[0],
           values[1],
           values[2],
           values[3]);
}

EXPORT(long double)testfunc_Ddd(double a, double b)
{
    long double result = (long double)(a * b);
    printf("testfunc_Ddd(%p, %p)\n", &a, &b);
    printf("testfunc_Ddd(%g, %g)\n", a, b);
    return result;
}

EXPORT(long double)testfunc_DDD(long double a, long double b)
{
    long double result = a * b;
    printf("testfunc_DDD(%p, %p)\n", &a, &b);
    printf("testfunc_DDD(%Lg, %Lg)\n", a, b);
    return result;
}

EXPORT(int)testfunc_iii(int a, int b)
{
    int result = a * b;
    printf("testfunc_iii(%p, %p)\n", &a, &b);
    return result;
}

EXPORT(int)myprintf(char *fmt, ...)
{
    int result;
    va_list argptr;
    va_start(argptr, fmt);
    result = vprintf(fmt, argptr);
    va_end(argptr);
    return result;
}

EXPORT(char *)my_strtok(char *token, const char *delim)
{
    return strtok(token, delim);
}

EXPORT(char *)my_strchr(const char *s, int c)
{
    return strchr(s, c);
}


EXPORT(double) my_sqrt(double a)
{
    return sqrt(a);
}

EXPORT(void) my_qsort(void *base, size_t num, size_t width, int(*compare)(const void*, const void*))
{
    qsort(base, num, width, compare);
}

EXPORT(int *) _testfunc_ai8(int a[8])
{
    return a;
}

EXPORT(void) _testfunc_v(int a, int b, int *presult)
{
    *presult = a + b;
}

EXPORT(int) _testfunc_i_bhilfd(signed char b, short h, int i, long l, float f, double d)
{
/*      printf("_testfunc_i_bhilfd got %d %d %d %ld %f %f\n",
               b, h, i, l, f, d);
*/
    return (int)(b + h + i + l + f + d);
}

EXPORT(float) _testfunc_f_bhilfd(signed char b, short h, int i, long l, float f, double d)
{
/*      printf("_testfunc_f_bhilfd got %d %d %d %ld %f %f\n",
               b, h, i, l, f, d);
*/
    return (float)(b + h + i + l + f + d);
}

EXPORT(double) _testfunc_d_bhilfd(signed char b, short h, int i, long l, float f, double d)
{
/*      printf("_testfunc_d_bhilfd got %d %d %d %ld %f %f\n",
               b, h, i, l, f, d);
*/
    return (double)(b + h + i + l + f + d);
}

EXPORT(long double) _testfunc_D_bhilfD(signed char b, short h, int i, long l, float f, long double d)
{
/*      printf("_testfunc_d_bhilfd got %d %d %d %ld %f %f\n",
               b, h, i, l, f, d);
*/
    return (long double)(b + h + i + l + f + d);
}

EXPORT(char *) _testfunc_p_p(void *s)
{
    return (char *)s;
}

EXPORT(void *) _testfunc_c_p_p(int *argcp, char **argv)
{
    return argv[(*argcp)-1];
}

EXPORT(void *) get_strchr(void)
{
    return (void *)strchr;
}

EXPORT(char *) my_strdup(char *src)
{
    char *dst = (char *)malloc(strlen(src)+1);
    if (!dst)
        return NULL;
    strcpy(dst, src);
    return dst;
}

EXPORT(void)my_free(void *ptr)
{
    free(ptr);
}

#ifndef MS_WIN32
# ifndef __stdcall
#  define __stdcall /* */
# endif
#endif

typedef struct {
    int (*c)(int, int);
    int (__stdcall *s)(int, int);
} FUNCS;

EXPORT(int) _testfunc_callfuncp(FUNCS *fp)
{
    fp->c(1, 2);
    fp->s(3, 4);
    return 0;
}

EXPORT(int) _testfunc_deref_pointer(int *pi)
{
    return *pi;
}

#ifdef MS_WIN32
EXPORT(int) _testfunc_piunk(IUnknown FAR *piunk)
{
    piunk->lpVtbl->AddRef(piunk);
    return piunk->lpVtbl->Release(piunk);
}
#endif

EXPORT(int) _testfunc_callback_with_pointer(int (*func)(int *))
{
    int table[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};

    return (*func)(table);
}

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

EXPORT (int) an_integer = 42;

EXPORT(int) get_an_integer(void)
{
    return an_integer;
}

EXPORT(double)
integrate(double a, double b, double (*f)(double), long nstep)
{
    double x, sum=0.0, dx=(b-a)/(double)nstep;
    for(x=a+0.5*dx; (b-x)*(x-a)>0.0; x+=dx)
        sum += f(x);
    return sum/(double)nstep;
}

typedef struct {
    void (*initialize)(void *(*)(int), void(*)(void *));
} xxx_library;

static void _xxx_init(void *(*Xalloc)(int), void (*Xfree)(void *))
{
    void *ptr;

    printf("_xxx_init got %p %p\n", Xalloc, Xfree);
    printf("calling\n");
    ptr = Xalloc(32);
    Xfree(ptr);
    printf("calls done, ptr was %p\n", ptr);
}

struct BITS {
    int A: 1, B:2, C:3, D:4, E: 5, F: 6, G: 7, H: 8, I: 9;
    short M: 1, N: 2, O: 3, P: 4, Q: 5, R: 6, S: 7;
};

DL_EXPORT(void) set_bitfields(struct BITS *bits, char name, int value)
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

DL_EXPORT(int) unpack_bitfields(struct BITS *bits, char name)
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

typedef struct {
    long x;
    long y;
} POINT;

typedef struct {
    long left;
    long top;
    long right;
    long bottom;
} RECT;

EXPORT(int) PointInRect(RECT *prc, POINT pt)
{
    if (pt.x < prc->left)
        return 0;
    if (pt.x > prc->right)
        return 0;
    if (pt.y < prc->top)
        return 0;
    if (pt.y > prc->bottom)
        return 0;
    return 1;
}

EXPORT(long left = 10);
EXPORT(long top = 20);
EXPORT(long right = 30);
EXPORT(long bottom = 40);

EXPORT(RECT) ReturnRect(int i, RECT ar, RECT* br, POINT cp, RECT dr,
                        RECT *er, POINT fp, RECT gr)
{
    /*Check input */
    if (ar.left + br->left + dr.left + er->left + gr.left != left * 5)
    {
        ar.left = 100;
        return ar;
    }
    if (ar.right + br->right + dr.right + er->right + gr.right != right * 5)
    {
        ar.right = 100;
        return ar;
    }
    if (cp.x != fp.x)
    {
        ar.left = -100;
    }
    if (cp.y != fp.y)
    {
        ar.left = -200;
    }
    switch(i)
    {
    case 0:
        return ar;
        break;
    case 1:
        return dr;
        break;
    case 2:
        return gr;
        break;

    }
    return ar;
}

typedef struct {
    short x;
    short y;
} S2H;

EXPORT(S2H) ret_2h_func(S2H inp)
{
    inp.x *= 2;
    inp.y *= 3;
    return inp;
}

typedef struct {
    int a, b, c, d, e, f, g, h;
} S8I;

EXPORT(S8I) ret_8i_func(S8I inp)
{
    inp.a *= 2;
    inp.b *= 3;
    inp.c *= 4;
    inp.d *= 5;
    inp.e *= 6;
    inp.f *= 7;
    inp.g *= 8;
    inp.h *= 9;
    return inp;
}

EXPORT(int) GetRectangle(int flag, RECT *prect)
{
    if (flag == 0)
        return 0;
    prect->left = (int)flag;
    prect->top = (int)flag + 1;
    prect->right = (int)flag + 2;
    prect->bottom = (int)flag + 3;
    return 1;
}

EXPORT(void) TwoOutArgs(int a, int *pi, int b, int *pj)
{
    *pi += a;
    *pj += b;
}
