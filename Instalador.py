import subprocess
import sys
import os
import ctypes
import urllib.request
import zipfile
import tempfile

APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.12.4/python-3.12.4-embed-amd64.zip"
PYTHON_EMBED_DIR = os.path.join(APP_DIR, "python_embed")
GETPIP_URL = "https://bootstrap.pypa.io/get-pip.py"

def hide_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except:
        pass

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)
    except:
        pass

def find_system_python():
    for p in ["python", "python3", "py"]:
        try:
            result = subprocess.run(
                [p, "--version"],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000
            )
            if result.returncode == 0 and "Python 3" in result.stdout:
                return p
        except:
            pass

    for path in [
        r"C:\Python312\python.exe",
        r"C:\Python313\python.exe",
        r"C:\Python314\python.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python312\python.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python313\python.exe"),
    ]:
        if os.path.exists(path):
            return path
    return None

def download_file(url, dest):
    urllib.request.urlretrieve(url, dest)

def setup_embed_python():
    if os.path.exists(os.path.join(PYTHON_EMBED_DIR, "python.exe")):
        return True

    os.makedirs(PYTHON_EMBED_DIR, exist_ok=True)

    zip_path = os.path.join(PYTHON_EMBED_DIR, "python.zip")
    download_file(PYTHON_EMBED_URL, zip_path)

    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(PYTHON_EMBED_DIR)
    os.remove(zip_path)

    pth_file = os.path.join(PYTHON_EMBED_DIR, "python312._pth")
    if os.path.exists(pth_file):
        with open(pth_file, "r") as f:
            content = f.read()
        content = content.replace("#import site", "import site")
        with open(pth_file, "w") as f:
            f.write(content)

    get_pip_path = os.path.join(PYTHON_EMBED_DIR, "get-pip.py")
    download_file(GETPIP_URL, get_pip_path)

    subprocess.run(
        [os.path.join(PYTHON_EMBED_DIR, "python.exe"), get_pip_path],
        capture_output=True, timeout=120
    )

    scripts_dir = os.path.join(PYTHON_EMBED_DIR, "Scripts")
    os.makedirs(scripts_dir, exist_ok=True)

    python_path = os.path.join(PYTHON_EMBED_DIR, "python.exe")
    subprocess.run(
        [python_path, "-m", "pip", "install", "PyQt6", "llama-cpp-python", "requests"],
        capture_output=True, timeout=600
    )

    return True

def ensure_dependencies(python_cmd):
    result = subprocess.run(
        [python_cmd, "-c", "import PyQt6; import llama_cpp"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        subprocess.run(
            [python_cmd, "-m", "pip", "install", "PyQt6", "llama-cpp-python", "requests"],
            capture_output=True, timeout=600
        )

def main():
    hide_console()

    python_cmd = find_system_python()

    if not python_cmd:
        try:
            setup_embed_python()
            python_cmd = os.path.join(PYTHON_EMBED_DIR, "python.exe")
        except Exception as e:
            msg = f"Error configurando Python: {e}\n\nInstala Python 3.12+ desde python.org"
            ctypes.windll.user32.MessageBoxW(0, msg, "Error", 0x10)
            return

    ensure_dependencies(python_cmd)

    main_script = os.path.join(APP_DIR, "main.py")
    if os.path.exists(main_script):
        subprocess.Popen(
            [python_cmd, main_script],
            cwd=APP_DIR,
            creationflags=0x08000000
        )
    else:
        ctypes.windll.user32.MessageBoxW(
            0, "No se encontro main.py", "Error", 0x10
        )

if __name__ == "__main__":
    main()
