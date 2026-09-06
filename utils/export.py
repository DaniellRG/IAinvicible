import os
from datetime import datetime


def conversation_to_markdown(messages: list[dict], title: str = "Conversacion") -> str:
    lines = [f"# {title}", ""]
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "assistant":
            lines.append("## IA\n")
        else:
            lines.append("## Usuario\n")
        lines.append(content.strip())
        lines.append("")
    return "\n".join(lines)


def save_conversation_markdown(messages: list[dict], title: str = "Conversacion",
                               folder: str = "") -> str:
    if not folder:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        exports_dir = os.path.join(app_dir, "exports")
        folder = exports_dir
    os.makedirs(folder, exist_ok=True)

    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip() or "Conversacion"
    safe_title = safe_title[:60]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(folder, f"{safe_title}_{timestamp}.md")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(conversation_to_markdown(messages, title))
    return filepath