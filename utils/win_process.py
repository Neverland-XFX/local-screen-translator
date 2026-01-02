import ctypes
import os
from ctypes import wintypes


_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

_USER32.GetForegroundWindow.restype = wintypes.HWND
_USER32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
_USER32.GetWindowThreadProcessId.restype = wintypes.DWORD
_KERNEL32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
_KERNEL32.OpenProcess.restype = wintypes.HANDLE
_KERNEL32.QueryFullProcessImageNameW.argtypes = (
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
)
_KERNEL32.QueryFullProcessImageNameW.restype = wintypes.BOOL
_KERNEL32.CloseHandle.argtypes = (wintypes.HANDLE,)
_KERNEL32.CloseHandle.restype = wintypes.BOOL


def get_foreground_process_path() -> str | None:
    hwnd = _USER32.GetForegroundWindow()
    if not hwnd:
        return None

    pid = wintypes.DWORD()
    _USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None

    handle = _KERNEL32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return None

    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if not _KERNEL32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return None
        return buf.value
    finally:
        _KERNEL32.CloseHandle(handle)


def _normalize_path(path: str) -> str:
    if not path:
        return ""
    path = path.strip().strip('"')
    return os.path.normcase(os.path.normpath(path))


def paths_match(left: str, right: str) -> bool:
    left_norm = _normalize_path(left)
    right_norm = _normalize_path(right)
    if not left_norm or not right_norm:
        return False
    if os.path.isdir(right_norm):
        right_norm = right_norm.rstrip(os.sep)
        return left_norm.startswith(right_norm + os.sep)
    return left_norm == right_norm
