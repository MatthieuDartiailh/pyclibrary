/* Test header for unions declaration */

// Test declaring an union.
typedef union union_name {
    int x = 1;
    int y;
} *union_name_ptr;

// Test defining an unnamed union
#pragma pack(push)
#pragma pack(16)
union
{
    int x;
    int y;
} no_name_union_inst;

#pragma pack(pop)
// Test defining a structure using an unnamed union internally.
typedef struct tagRID_DEVICE_INFO {
    DWORD cbSize;
    DWORD dwType;
    union {
        RID_DEVICE_INFO_MOUSE mouse;
        RID_DEVICE_INFO_KEYBOARD keyboard;
        RID_DEVICE_INFO_HID hid;
    };
} RID_DEVICE_INFO, *PRID_DEVICE_INFO, *LPRID_DEVICE_INFO;
