import os
import sys
import shutil
import tempfile


def cleanup_on_exit():
    temp_dirs = [
        os.path.join(tempfile.gettempdir(), "ia_invicible"),
    ]
    for d in temp_dirs:
        if os.path.exists(d):
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass


def clear_env_vars():
    env_keys_to_clear = [
        "AI_INVICIBLE_SESSION",
        "AI_INVICIBLE_MODEL",
    ]
    for key in env_keys_to_clear:
        if key in os.environ:
            del os.environ[key]


def get_app_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_models_dir() -> str:
    app_dir = get_app_dir()
    models_dir = os.path.join(app_dir, "models")
    os.makedirs(models_dir, exist_ok=True)
    return models_dir


def get_temp_dir() -> str:
    temp = os.path.join(tempfile.gettempdir(), "ia_invicible")
    os.makedirs(temp, exist_ok=True)
    return temp


def cleanup_temp():
    temp = os.path.join(tempfile.gettempdir(), "ia_invicible")
    if os.path.exists(temp):
        try:
            shutil.rmtree(temp, ignore_errors=True)
        except Exception:
            pass
