/* File used to test the handling of the pragma pack*/

// Use default packing
#pragma pack()   // n defaults to 8; equivalent to /Zp8

// Change default packing
#pragma pack(4)   // n = 4

// Push and select custom packing
#define PACKING 16
#pragma pack(push, r1, PACKING)   // n = 16, pushed to stack

// Change packing back to default
#pragma pack()

// Push current packing to stack (twice for pop test)
#pragma pack(push, r2)
#pragma pack(push, r3, 4)

// Remove packing
#pragma pack(pop, r2)
#pragma pack(pop)

// Test handling of unknown pragmas
#pragma omp parallel
