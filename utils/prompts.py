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


def new_prompt_name() -> str:
    os.makedirs(PROMPTS_DIR, exist_ok=True)
    index = 1
    while True:
        name = f"Prompt {index}.md"
        if not prompt_exists(name):
            return name
        index += 1