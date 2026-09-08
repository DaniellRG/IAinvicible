import sys
import os
import ctypes

APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

def hide_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass

def apply_process_stealth():
    """Aplica todas las tecnicas de stealth de proceso al inicio."""
    try:
        from core.anti_capture import hide_from_processes, detach_console
        hide_from_processes()
        detach_console()
    except Exception:
        pass
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass

def main():
    hide_console()
    apply_process_stealth()

    os.chdir(APP_DIR)
    sys.path.insert(0, APP_DIR)

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Notas")
    app.setOrganizationName("Microsoft")

    font = QFont("Segoe UI", 13)
    app.setFont(font)

    window = MainWindow()
    window.show()

    app.aboutToQuit.connect(lambda: _cleanup())

    sys.exit(app.exec())

def _cleanup():
    from utils.cleanup import cleanup_on_exit, clear_env_vars
    clear_env_vars()
    cleanup_on_exit()

if __name__ == "__main__":
    main()
