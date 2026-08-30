import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WDA_EXCLUDEFROMCAPTURE = 0x00000011
WDA_NONE = 0x00000000

WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000

GWL_EXSTYLE = -20
GWL_STYLE = -16

SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2

WM_HOTKEY = 0x0312
MOD_CONTROL = 0x0002
MOD_ALT = 0x0001
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000

VK_OEM_3 = 0xC0

SetWindowDisplayAffinity = user32.SetWindowDisplayAffinity
SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
SetWindowDisplayAffinity.restype = wintypes.BOOL

GetWindowLongW = user32.GetWindowLongW
GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
GetWindowLongW.restype = ctypes.c_long

SetWindowLongW = user32.SetWindowLongW
SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
SetWindowLongW.restype = ctypes.c_long

SetWindowPos = user32.SetWindowPos
SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND,
    ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int,
    wintypes.UINT
]
SetWindowPos.restype = wintypes.BOOL

FindWindowW = user32.FindWindowW
FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
FindWindowW.restype = wintypes.HWND

GetForegroundWindow = user32.GetForegroundWindow
GetForegroundWindow.restype = wintypes.HWND

SetWindowTextW = user32.SetWindowTextW
SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
SetWindowTextW.restype = wintypes.BOOL

RegisterHotKey = user32.RegisterHotKey
RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
RegisterHotKey.restype = wintypes.BOOL

UnregisterHotKey = user32.UnregisterHotKey
UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
UnregisterHotKey.restype = wintypes.BOOL

ShowWindow = user32.ShowWindow
SW_HIDE = 0
SW_SHOW = 5

HOTKEY_ID_TOGGLE = 1


def exclude_from_capture(hwnd: int) -> bool:
    result = SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
    return bool(result)


def restore_capture(hwnd: int) -> bool:
    result = SetWindowDisplayAffinity(hwnd, WDA_NONE)
    return bool(result)


def hide_from_taskbar(hwnd: int) -> bool:
    """Oculta la ventana de la barra de tareas y de Alt+Tab."""
    style = GetWindowLongW(hwnd, GWL_EXSTYLE)
    style = style | WS_EX_TOOLWINDOW
    style = style & ~WS_EX_APPWINDOW
    result = SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    return result != 0


def hide_from_alt_tab(hwnd: int) -> bool:
    """Oculta la ventana de Alt+Tab."""
    style = GetWindowLongW(hwnd, GWL_EXSTYLE)
    style = style | WS_EX_TOOLWINDOW
    style = style & ~WS_EX_APPWINDOW
    result = SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    return result != 0


def set_noactivate(hwnd: int) -> bool:
    """La ventana no roba foco."""
    style = GetWindowLongW(hwnd, GWL_EXSTYLE)
    style = style | WS_EX_NOACTIVATE
    result = SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    return result != 0


def set_topmost(hwnd: int) -> bool:
    result = SetWindowPos(
        hwnd, HWND_TOPMOST,
        0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
    )
    return bool(result)


def remove_topmost(hwnd: int) -> bool:
    result = SetWindowPos(
        hwnd, HWND_NOTOPMOST,
        0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
    )
    return bool(result)


def set_window_title(hwnd: int, title: str) -> bool:
    result = SetWindowTextW(hwnd, title)
    return bool(result)


def get_active_window_title() -> str:
    hwnd = GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def find_window(class_name: str = None, window_name: str = None) -> int:
    hwnd = FindWindowW(class_name, window_name)
    return hwnd


def setup_stealth_window(hwnd: int) -> bool:
    """Configura la ventana completa para ser stealth."""
    hide_from_taskbar(hwnd)
    hide_from_alt_tab(hwnd)
    exclude_from_capture(hwnd)
    set_window_title(hwnd, "Notas.txt - Bloc de notas")
    return True


def register_hotkey(hwnd: int, hotkey_id: int = HOTKEY_ID_TOGGLE,
                    modifiers: int = MOD_CONTROL, vk_code: int = VK_OEM_3) -> bool:
    """Registra un hotkey global. Ctrl+` por defecto."""
    result = RegisterHotKey(hwnd, hotkey_id, modifiers, vk_code)
    return bool(result)


def unregister_hotkey(hwnd: int, hotkey_id: int = HOTKEY_ID_TOGGLE) -> bool:
    """Des-registra el hotkey global."""
    result = UnregisterHotKey(hwnd, hotkey_id)
    return bool(result)


def is_hotkey_message(msg) -> bool:
    """Verifica si un mensaje es del hotkey."""
    try:
        return msg.message == WM_HOTKEY
    except Exception:
        return False
