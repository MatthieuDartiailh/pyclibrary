/* This file is used to test the processing of conditional macros. */

#define MACRO

// Test if defined
#if defined MACRO
    #define DEFINE_IF
    int DECLARE_IF;
#endif

#if defined UNDEFINED
  #define NO_DEFINE_IF
  int NO_DECLARE_IF;
#endif

// Test ifdef
#ifdef MACRO
  #define DEFINE_IFDEF
  int DECLARE_IFDEF;
#endif

#ifdef UNDEFINED
  #define NO_DEFINE_IFDEF
  int NO_DECLARE_IFDEF;
#endif

// Test if !defined
#if !defined UNDEFINED
  #define DEFINE_IFN
  int DECLARE_IFN;
#endif

#if !defined MACRO
  #define NO_DEFINE_IFN
  int NO_DECLARE_IFN;
#endif

// Test ifndef
#ifndef UNDEFINED
  #define DEFINE_IFNDEF
  int DECLARE_IFNDEF;
#endif

#ifndef MACRO
  #define NO_DEFINE_IFNDEF
  int NO_DECLARE_IFNDEF;
#endif

// Test elif
#ifdef UNDEFINED
  #define NO_DEFINE_ELIF
  int NO_DECLARE_ELIF;
#elif defined MACRO
  #define DEFINE_ELIF
  int DECLARE_ELIF;
#endif

// Test else
#ifdef UNDEFINED
  #define NO_DEFINE_ELSE
  int NO_DECLARE_ELSE;
#else
  #define DEFINE_ELSE
  int DECLARE_ELSE;
#endif

// Test nested
#if !defined MACRO_N1
#  define DEFINE_N1
   int DECLARE_N1;
#  ifdef DEFINE_N2
#    define NO_DEFINE_N2
#  endif
#else
#  define DEFINE_N2
#endif

#ifndef DEFINE_N3
  #define DEFINE_N3 10
  #ifndef DEFINE_N3
    #define NO_DEFINE_N3
    int NO_DECLARE_N3;
  #endif
#endif

// Test logical operations
#define VAL1 6

#if defined MACRO && VAL1 < 5
  #define NO_DEFINE_LOG
  int NO_DECLARE_LOG;
#elif defined MACRO && VAL1 > 5
  #define DEFINE_LOG
  int DECLARE_LOG;
#endif

// Test undef
#define UNDEF
#ifdef UNDEF
    #define DEFINE_UNDEF
#endif
#undef UNDEF
