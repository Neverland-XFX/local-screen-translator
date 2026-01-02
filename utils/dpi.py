import ctypes


def set_process_dpi_awareness() -> bool:
    try:
        awareness_context = ctypes.c_void_p(-4)  # PER_MONITOR_AWARE_V2
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(awareness_context):
            return True
    except Exception:
        pass

    try:
        # 2 = PER_MONITOR_AWARE
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:
            return True
    except Exception:
        pass

    try:
        if ctypes.windll.user32.SetProcessDPIAware():
            return True
    except Exception:
        pass

    return False
