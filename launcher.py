import sys
import os
import ctypes

APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

def hide_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except:
        pass

def rename_process():
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetProcessNameW("svchost.exe")
    except:
        pass

def main():
    hide_console()
    rename_process()

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
