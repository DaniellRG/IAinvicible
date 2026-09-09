import sys
import os
import ctypes

def hide_console():
    """Oculta la ventana de consola completamente."""
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass

hide_console()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.anti_capture import hide_from_processes, detach_console


def apply_process_stealth():
    """Aplica todas las tecnicas de stealth de proceso al inicio."""
    try:
        hide_from_processes()
    except Exception:
        pass
    try:
        detach_console()
    except Exception:
        pass
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass


from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from core.single_instance import SingleInstanceGuard
from core.tooltips import install_tooltip_blocker
from ui.main_window import MainWindow


def main():
    apply_process_stealth()

    app = QApplication(sys.argv)
    app.setApplicationName("Notas")
    app.setOrganizationName("Microsoft")
    install_tooltip_blocker(app)

    guard = SingleInstanceGuard()
    if not guard.acquire():
        # Ya hay una instancia abierta: le pedimos que se muestre y salimos.
        return 0

    font = QFont("Consolas", 13)
    app.setFont(font)

    window = MainWindow()
    window.show()

    def _show_window():
        try:
            window.show_from_second_instance()
        except Exception:
            pass

    guard.on_show = _show_window

    def _quit():
        try:
            guard.close()
        except Exception:
            pass
        _cleanup()

    app.aboutToQuit.connect(_quit)

    sys.exit(app.exec())


def _cleanup():
    from utils.cleanup import cleanup_on_exit, clear_env_vars
    clear_env_vars()
    cleanup_on_exit()


if __name__ == "__main__":
    main()
