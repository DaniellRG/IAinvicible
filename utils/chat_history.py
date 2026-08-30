import json
import os
import time

HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "history")


def _ensure_dir():
    os.makedirs(HISTORY_DIR, exist_ok=True)


def save_conversation(title: str, messages: list[dict], conversation_id: str = None) -> str:
    _ensure_dir()
    if not conversation_id:
        conversation_id = str(int(time.time() * 1000))

    data = {
        "id": conversation_id,
        "title": title,
        "messages": messages,
        "timestamp": time.time(),
    }

    filepath = os.path.join(HISTORY_DIR, f"{conversation_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return conversation_id


def load_conversation(conversation_id: str) -> dict | None:
    filepath = os.path.join(HISTORY_DIR, f"{conversation_id}.json")
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def list_conversations() -> list[dict]:
    _ensure_dir()
    conversations = []
    for fname in os.listdir(HISTORY_DIR):
        if fname.endswith(".json"):
            filepath = os.path.join(HISTORY_DIR, fname)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                conversations.append({
                    "id": data.get("id", fname.replace(".json", "")),
                    "title": data.get("title", "Sin titulo"),
                    "timestamp": data.get("timestamp", 0),
                    "msg_count": len(data.get("messages", [])),
                })
            except Exception:
                pass

    conversations.sort(key=lambda x: x["timestamp"], reverse=True)
    return conversations


def delete_conversation(conversation_id: str):
    filepath = os.path.join(HISTORY_DIR, f"{conversation_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)


def generate_title(messages: list[dict]) -> str:
    for msg in messages:
        if msg.get("role") == "user":
            text = msg.get("content", "")[:50]
            if len(msg.get("content", "")) > 50:
                text += "..."
            return text if text else "Conversacion"
    return "Conversacion"
