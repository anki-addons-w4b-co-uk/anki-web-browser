import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True)

INPUT_MOUSE    = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

KEY_EVENT_F_EXTENDED_KEY = 0x0001
KEY_EVENT_F_KEY_UP       = 0x0002
KEY_EVENT_F_UNICODE     = 0x0004
KEY_EVENT_F_SCANCODE    = 0x0008

MAP_VK_TO_VSC = 0

# msdn.microsoft.com/en-us/library/dd375731
VK_A = 0x41
VK_ALT = 0x12
VK_CTRL = 0x11
VK_DEL = 0x2E
VK_S = 0x53
VK_TAB = 0x09
VK_V = 0x56

# C struct definitions

wintypes.ULONG_PTR = wintypes.WPARAM

class MouseInput(ctypes.Structure):
    _fields_ = (("dx",          wintypes.LONG),
                ("dy",          wintypes.LONG),
                ("mouseData",   wintypes.DWORD),
                ("dwFlags",     wintypes.DWORD),
                ("time",        wintypes.DWORD),
                ("dwExtraInfo", wintypes.ULONG_PTR))

class KeyboardInput(ctypes.Structure):
    _fields_ = (("wVk",         wintypes.WORD),
                ("wScan",       wintypes.WORD),
                ("dwFlags",     wintypes.DWORD),
                ("time",        wintypes.DWORD),
                ("dwExtraInfo", wintypes.ULONG_PTR))

    def __init__(self, *args, **kwds):
        super(KeyboardInput, self).__init__(*args, **kwds)
        # some programs use the scan code even if KEYEVENTF_SCANCODE
        # isn't set in dwFflags, so attempt to map the correct code.
        if not self.dwFlags & KEY_EVENT_F_UNICODE:
            self.wScan = user32.MapVirtualKeyExW(self.wVk,
                                                 MAP_VK_TO_VSC, 0)

class HardwareInput(ctypes.Structure):
    _fields_ = (("uMsg",    wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD))

class Input(ctypes.Structure):
    class _Input(ctypes.Union):
        _fields_ = (("ki", KeyboardInput),
                    ("mi", MouseInput),
                    ("hi", HardwareInput))
    _anonymous_ = ("_input",)
    _fields_ = (("type",   wintypes.DWORD),
                ("_input", _Input))

LP_INPUT = ctypes.POINTER(Input)

def _check_count(result, func, args):
    if result == 0:
        raise ctypes.WinError(ctypes.get_last_error())
    return args

user32.SendInput.errcheck = _check_count
user32.SendInput.argtypes = (wintypes.UINT,  # nInputs
                             LP_INPUT,  # pInputs
                             ctypes.c_int)  # cbSize

# Functions

def press_key(hex_key_code):
    x = Input(type=INPUT_KEYBOARD,
              ki=KeyboardInput(wVk=hex_key_code))
    user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))

def release_key(hex_key_code):
    x = Input(type=INPUT_KEYBOARD,
              ki=KeyboardInput(wVk=hex_key_code,
                               dwFlags=KEY_EVENT_F_KEY_UP))
    user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))

def delete():
    press_key(VK_DEL)
    release_key(VK_DEL)
    return

def press_alt_s():
    press_key(VK_ALT)
    press_key(VK_S)
    release_key(VK_S)
    release_key(VK_ALT)
    return

def paste():
    press_key(VK_CTRL)
    press_key(VK_V)
    release_key(VK_V)
    release_key(VK_CTRL)
    return

def select_all():
    press_key(VK_CTRL)
    press_key(VK_A)
    release_key(VK_A)
    release_key(VK_CTRL)
    return
