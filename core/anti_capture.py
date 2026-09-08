import ctypes
import os
import struct
import sys
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
dwmapi = ctypes.windll.dwmapi

ntdll = ctypes.WinDLL("ntdll", use_last_error=True)

ntdll.NtQueryInformationProcess.restype = ctypes.c_long
ntdll.NtQueryInformationProcess.argtypes = [
    wintypes.HANDLE, ctypes.c_ulong, ctypes.c_void_p,
    ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
]
ProcessBasicInformation = 0
ProcessWow64Information = 0x1A

DWMWA_TRANSITIONS_FORCEDISABLED = 3

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

VK_Z = 0x5A

SetWindowDisplayAffinity = user32.SetWindowDisplayAffinity
SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
SetWindowDisplayAffinity.restype = wintypes.BOOL

GetWindowDisplayAffinity = user32.GetWindowDisplayAffinity
GetWindowDisplayAffinity.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
GetWindowDisplayAffinity.restype = wintypes.BOOL

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


def get_window_display_affinity(hwnd: int) -> int:
    value = wintypes.DWORD(0)
    try:
        if GetWindowDisplayAffinity(hwnd, ctypes.byref(value)):
            return value.value
    except Exception:
        pass
    return WDA_NONE


def is_excluded_from_capture(hwnd: int) -> bool:
    return get_window_display_affinity(hwnd) == WDA_EXCLUDEFROMCAPTURE


def restore_capture(hwnd: int) -> bool:
    result = SetWindowDisplayAffinity(hwnd, WDA_NONE)
    return bool(result)


RedrawWindow = user32.RedrawWindow
RedrawWindow.argtypes = [wintypes.HWND, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
RedrawWindow.restype = wintypes.BOOL

RDW_INVALIDATE = 0x0001
RDW_UPDATENOW = 0x0100


def redraw_window(hwnd: int) -> bool:
    result = RedrawWindow(hwnd, None, 0, RDW_INVALIDATE | RDW_UPDATENOW)
    return bool(result)


DwmSetWindowAttribute = dwmapi.DwmSetWindowAttribute
DwmSetWindowAttribute.argtypes = [
    wintypes.HWND, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD
]
DwmSetWindowAttribute.restype = ctypes.c_long


def disable_window_transitions(hwnd: int) -> bool:
    value = ctypes.c_int(1)
    result = DwmSetWindowAttribute(
        hwnd, DWMWA_TRANSITIONS_FORCEDISABLED,
        ctypes.byref(value), ctypes.sizeof(value)
    )
    return result == 0


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
    disable_window_transitions(hwnd)
    set_window_title(hwnd, "Notas.txt - Bloc de notas")
    return True


def register_hotkey(hwnd: int, hotkey_id: int = HOTKEY_ID_TOGGLE,
                    modifiers: int = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT,
                    vk_code: int = VK_Z) -> bool:
    """Registra un hotkey global. Ctrl+Alt+Z por defecto (sin auto-repeticion)."""
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


# ---------------------------------------------------------------------------
#  STEALTH DE PROCESO
# ---------------------------------------------------------------------------

GetCurrentProcess = kernel32.GetCurrentProcess
GetCurrentProcess.restype = wintypes.HANDLE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [
    wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t),
]
ReadProcessMemory.restype = wintypes.BOOL

WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [
    wintypes.HANDLE, wintypes.LPVOID, wintypes.LPCVOID,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t),
]
WriteProcessMemory.restype = wintypes.BOOL

FreeConsole = kernel32.FreeConsole
FreeConsole.argtypes = []
FreeConsole.restype = wintypes.BOOL

IsWow64Process = kernel32.IsWow64Process
IsWow64Process.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
IsWow64Process.restype = wintypes.BOOL

_set_process_name_w = None


def _try_set_process_name(name: str) -> bool:
    """Intenta renombrar el proceso. SetProcessNameW no existe en kernel32,
    por lo que se busca la API por nombre solo de forma opcional y segura."""
    global _set_process_name_w
    try:
        if _set_process_name_w is None:
            _set_process_name_w = getattr(kernel32, "SetProcessNameW", None)
            if _set_process_name_w is None:
                return False
            _set_process_name_w.argtypes = [wintypes.LPCWSTR]
            _set_process_name_w.restype = wintypes.BOOL
        if _set_process_name_w:
            return bool(_set_process_name_w(name))
    except Exception:
        pass
    return False


def _is_wow64() -> bool:
    """True si el proceso Python es de 32 bits ejecutandose en 64."""
    result = wintypes.BOOL(False)
    IsWow64Process(GetCurrentProcess(), ctypes.byref(result))
    return bool(result)


def _get_peb_address() -> int:
    """Obtiene la direccion base del PEB del proceso actual."""
    class PROCESS_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("Reserved1", ctypes.c_void_p),
            ("PebBaseAddress", ctypes.c_void_p),
            ("Reserved2", ctypes.c_void_p * 2),
            ("UniqueProcessId", wintypes.ULONG),
            ("Reserved3", ctypes.c_void_p),
        ]

    pbi = PROCESS_BASIC_INFORMATION()
    ret_len = wintypes.ULONG(0)
    status = ntdll.NtQueryInformationProcess(
        GetCurrentProcess(),
        ProcessBasicInformation,
        ctypes.byref(pbi),
        ctypes.sizeof(pbi),
        ctypes.byref(ret_len),
    )
    if status >= 0 and pbi.PebBaseAddress:
        return ctypes.cast(pbi.PebBaseAddress, ctypes.c_void_p).value
    return 0


def _read_memory(address: int, size: int) -> bytes:
    """Lee memoria del proceso actual."""
    buf = ctypes.create_string_buffer(size)
    bytes_read = ctypes.c_size_t(0)
    result = ReadProcessMemory(
        GetCurrentProcess(),
        ctypes.c_void_p(address),
        buf,
        size,
        ctypes.byref(bytes_read),
    )
    if not result:
        return b""
    return buf.raw[: bytes_read.value]


def _write_memory(address: int, data: bytes) -> bool:
    """Escribe memoria del proceso actual."""
    buf = ctypes.create_string_buffer(data)
    bytes_written = ctypes.c_size_t(0)
    result = WriteProcessMemory(
        GetCurrentProcess(),
        ctypes.c_void_p(address),
        buf,
        len(data),
        ctypes.byref(bytes_written),
    )
    return bool(result)


def _spoof_peb_name() -> bool:
    """
    Modifica el ImagePathName en el PEB del proceso para que las herramientas
    de depuracion y procesos muestren un nombre generico en lugar del real.
    """
    if _is_wow64():
        return False

    try:
        peb = _get_peb_address()
        if not peb:
            return False

        ptr_size = 8

        ldr_offset = peb + 0x18
        ldr_data = struct.unpack("<Q", _read_memory(ldr_offset, ptr_size))[0]
        if not ldr_data:
            return False

        in_load_order_offset = ldr_data + 0x10
        first_entry = struct.unpack("<Q", _read_memory(in_load_order_offset, ptr_size))[0]
        if not first_entry:
            return False

        dll_base_offset = first_entry + 0x30
        full_dll_name_offset = first_entry + 0x48

        _read_memory(dll_base_offset, ptr_size)

        name_unicode_offset = full_dll_name_offset
        name_unicode = _read_memory(name_unicode_offset, 16)
        if not name_unicode or len(name_unicode) < 16:
            return False

        if ptr_size == 8:
            name_len = struct.unpack("<H", name_unicode[0:2])[0]
            name_max = struct.unpack("<H", name_unicode[2:4])[0]
            name_buf_ptr = struct.unpack("<Q", name_unicode[8:16])[0]
        else:
            name_len = struct.unpack("<H", name_unicode[0:2])[0]
            name_max = struct.unpack("<H", name_unicode[2:4])[0]
            name_buf_ptr = struct.unpack("<I", name_unicode[8:12])[0]

        if not name_buf_ptr or name_len == 0:
            return False

        spoof_candidates = [
            "\\Windows\\System32\\svchost.exe",
            "\\Windows\\svchost.exe",
            "svchost.exe",
            "rundll32.exe",
            "conhost.exe",
        ]
        spoofed_name = None
        for candidate in spoof_candidates:
            if len(candidate.encode("utf-16-le")) + 2 <= name_max:
                spoofed_name = candidate
                break
        if spoofed_name is None:
            return False

        spoofed_bytes = spoofed_name.encode("utf-16-le")

        _write_memory(name_buf_ptr, spoofed_bytes + b"\x00\x00")

        if len(spoofed_bytes) < name_len:
            _write_memory(
                name_buf_ptr + len(spoofed_bytes),
                b"\x00\x00" * ((name_len - len(spoofed_bytes)) // 2),
            )

        new_len = len(spoofed_bytes)
        _write_memory(name_unicode_offset, struct.pack("<HH", new_len, name_max))

        return True
    except Exception:
        return False


def _spoof_peb_commandline() -> bool:
    """
    Modifica el CommandLine en el PEB del proceso para ocultar los argumentos
    reales de lanzamiento y mostrar uno generico de Windows.

    El offset del campo CommandLine varia entre versiones de Windows, por lo
    que se localiza dinamicamente comparando con GetCommandLineW().
    """
    if _is_wow64():
        return False

    try:
        peb = _get_peb_address()
        if not peb:
            return False

        ptr_size = 8

        GetCommandLineW = kernel32.GetCommandLineW
        GetCommandLineW.restype = ctypes.c_void_p
        real_cmd_ptr = GetCommandLineW()
        if not real_cmd_ptr:
            return False

        process_parameters = struct.unpack(
            "<Q", _read_memory(peb + 0x20, ptr_size)
        )[0]
        if not process_parameters:
            return False

        commandline_offset = 0
        cmd_len = 0
        cmd_max = 0
        cmd_buf_ptr = 0

        for candidate in range(0x38, 0x160, 8):
            chunk = _read_memory(process_parameters + candidate, 16)
            if not chunk or len(chunk) < 16:
                continue
            candidate_len, candidate_max = struct.unpack("<HH", chunk[0:4])
            candidate_buf = struct.unpack("<Q", chunk[8:16])[0]
            if (
                0 < candidate_len <= candidate_max <= 65536
                and candidate_buf == real_cmd_ptr
            ):
                commandline_offset = candidate
                cmd_len = candidate_len
                cmd_max = candidate_max
                cmd_buf_ptr = candidate_buf
                break

        if not commandline_offset or not cmd_buf_ptr or cmd_len == 0:
            return False

        spoof_candidates = [
            "C:\\Windows\\system32\\svchost.exe -k netsvcs -p",
            "C:\\Windows\\system32\\svchost.exe -k LocalServiceNetworkRestricted",
            "svchost.exe -k netsvcs -p",
            "C:\\Windows\\System32\\rundll32.exe",
        ]
        spoofed = None
        for candidate in spoof_candidates:
            if len(candidate.encode("utf-16-le")) + 2 <= cmd_max:
                spoofed = candidate
                break
        if spoofed is None:
            spoofed = "svchost.exe -k"
            if len(spoofed.encode("utf-16-le")) + 2 > cmd_max:
                return False

        spoofed_bytes = spoofed.encode("utf-16-le")

        _write_memory(cmd_buf_ptr, spoofed_bytes + b"\x00\x00")

        if len(spoofed_bytes) < cmd_len:
            _write_memory(
                cmd_buf_ptr + len(spoofed_bytes),
                b"\x00\x00" * ((cmd_len - len(spoofed_bytes)) // 2),
            )

        _write_memory(
            process_parameters + commandline_offset,
            struct.pack("<HH", len(spoofed_bytes), cmd_max),
        )

        return True
    except Exception:
        return False


def detach_console() -> bool:
    """Desacopla la consola del proceso para que no aparezca como consola."""
    try:
        return bool(FreeConsole())
    except Exception:
        return False


def hide_from_processes() -> bool:
    """
    Aplica tecnicas de stealth a nivel de proceso:
    - Oculta la consola
    - Renombra el proceso a un nombre generico de Windows
    - Modifica el nombre en el PEB
    """
    ok = True

    ok = detach_console() or ok

    _try_set_process_name("svchost.exe")

    try:
        if _spoof_peb_name():
            ok = True
    except Exception:
        pass

    return ok


def spoof_process_visibility() -> bool:
    """
    Cambia lo que se ve del proceso en herramientas externas.
    Retorna True si al menos una tecnica funciono.
    """
    ok = False
    try:
        if _spoof_peb_name():
            ok = True
    except Exception:
        pass

    try:
        if _spoof_peb_commandline():
            ok = True
    except Exception:
        pass

    _try_set_process_name("svchost.exe")

    return ok
