// File used to test the handling of the pragma pack
// ATTENTION: Do not remove/insert lines, as test is tied to line numbers!
//

// test correct line numbers on
#if 0

// Test handling of unknown pragmas
#pragma omp parallel
#pragma pack(4)  // has to be ignored
#define X
#undef X

#endif


// Use default packing
#pragma pack()   // line17: n defaults to 8; equivalent to /Zp8

// Change default packing
#pragma pack(4)   // line20: n = 4

// Push and select custom packing
#define PACKING 16
#pragma pack(push, r1, PACKING)   // line24: n = 16, pushed to stack

// Change packing back to default
#pragma pack()   line27:

// Push current packing to stack (twice for pop test)
#pragma pack(push, r2) //line30
#pragma pack(push, r3, 4)    //line31

// Remove packing
#pragma pack(pop, r2)   //line34
#pragma pack(pop)   //line35
