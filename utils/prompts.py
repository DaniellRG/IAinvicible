import os

PROMPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts"
)

_EXTENSIONS = (".md", ".txt")


def _full_path(name: str) -> str:
    if not name:
        return ""
    name = os.path.basename(name.strip())
    if not name:
        return ""
    if name.lower().endswith(_EXTENSIONS):
        return os.path.join(PROMPTS_DIR, name)
    return os.path.join(PROMPTS_DIR, name + ".md")


def list_prompts() -> list:
    os.makedirs(PROMPTS_DIR, exist_ok=True)
    names = []
    try:
        for entry in os.listdir(PROMPTS_DIR):
            if entry.lower().endswith(_EXTENSIONS):
                names.append(entry)
    except Exception:
        pass
    return sorted(names)


def prompt_exists(name: str) -> bool:
    path = _full_path(name)
    return bool(path) and os.path.exists(path)


def read_prompt(name: str) -> str:
    path = _full_path(name)
    if not path or not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save_prompt(name: str, content: str) -> str:
    os.makedirs(PROMPTS_DIR, exist_ok=True)
    path = _full_path(name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def delete_prompt(name: str):
    path = _full_path(name)
    try:
        if path and os.path.exists(path):
            os.remove(path)
            return True
    except Exception:
        pass
    return False


def rename_prompt(old_name: str, new_name: str) -> str:
    """Renombra el archivo de un prompt. Devuelve la ruta final o '' si falla."""
    old_path = _full_path(old_name)
    new_name = new_name.strip()
    if not old_path or not os.path.exists(old_path) or not new_name:
        return ""
    new_path = _full_path(new_name)
    if not new_path or new_path == old_path:
        return new_path
    if new_path.lower() == old_path.lower():
        return new_path
    if os.path.exists(new_path):
        return ""
    os.makedirs(PROMPTS_DIR, exist_ok=True)
    os.replace(old_path, new_path)
    return new_path


def new_prompt_name() -> str:
    os.makedirs(PROMPTS_DIR, exist_ok=True)
    index = 1
    while True:
        name = f"Prompt {index}.md"
        if not prompt_exists(name):
            return name
        index += 1