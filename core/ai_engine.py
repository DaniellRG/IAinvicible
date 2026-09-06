import json
import os
from typing import Generator, Optional

from .ollama_client import OllamaClient
from .cloud_client import CloudClient
from .local_gguf import LocalGGUFClient


CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

DEFAULT_CONFIG = {
    "cloud": {
        "provider": "openai",
        "api_key": "",
        "model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
    },
    "local": {
        "ollama_url": "http://localhost:11434",
        "model": "llama3.2:3b",
    },
    "ui": {
        "window_title": "Notas.txt - Bloc de notas",
        "theme": "dark",
        "font_size": 13,
    },
    "ai": {
        "system_prompt": (
            "Eres un asistente util y preciso. Responde de forma clara y concisa. "
            "Si te piden resolver un ejercicio o problema, muestra el razonamiento paso a paso. "
            "Responde en el idioma que te hablen."
        ),
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_messages": 20,
    },
}

DEFAULT_SYSTEM_PROMPT = DEFAULT_CONFIG["ai"]["system_prompt"]


def estimate_tokens(text: str) -> int:
    """Aproximacion de tokens: ~4 caracteres por token."""
    return max(1, len(text) // 4)


class AIEngine:
    def __init__(self):
        self.config = self._load_config()
        self.ollama = OllamaClient(
            base_url=self.config.get("local", {}).get("ollama_url", "http://localhost:11434")
        )
        self.cloud = CloudClient(
            api_key=self.config.get("cloud", {}).get("api_key", ""),
            base_url=self.config.get("cloud", {}).get("base_url", "https://api.openai.com/v1"),
            provider=self.config.get("cloud", {}).get("provider", "openai"),
        )
        self.local_gguf = LocalGGUFClient()

        stored_provider = self.config.get("ai", {}).get("provider", "ollama")
        self.current_provider = stored_provider

        if self.current_provider == "cloud":
            self.current_model = self.config.get("cloud", {}).get("model", "")
        elif self.current_provider == "local_file":
            self.current_model = self.config.get("local_file", {}).get("model", "")
        else:
            self.current_model = self.config.get("local", {}).get("model", "")

        self.conversation_history: list[dict] = []
        self.system_prompt = self.config.get("ai", {}).get("system_prompt", DEFAULT_SYSTEM_PROMPT)

    def _load_config(self) -> dict:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except Exception:
            loaded = {}

        config = {}
        for section, defaults in DEFAULT_CONFIG.items():
            merged = dict(defaults)
            merged.update(loaded.get(section, {}))
            config[section] = merged
        return config

    def save_config(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def set_api_key(self, key: str):
        self.config["cloud"]["api_key"] = key
        self.cloud.set_api_key(key)
        self.save_config()

    def set_cloud_provider(self, provider: str, base_url: str):
        self.config["cloud"]["provider"] = provider
        self.config["cloud"]["base_url"] = base_url
        self.cloud.set_provider(provider, base_url)
        self.save_config()

    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt
        self.config["ai"]["system_prompt"] = prompt
        self.save_config()

    def set_temperature(self, temperature: float):
        self.config["ai"]["temperature"] = max(0.0, min(2.0, temperature))
        self.save_config()

    def set_model(self, provider: str, model: str):
        if self.current_provider == "local_file" and provider != "local_file":
            self.local_gguf.unload_model()
        self.current_provider = provider
        self.current_model = model
        self.config["ai"]["provider"] = provider
        if provider == "cloud":
            self.config["cloud"]["model"] = model
        elif provider == "local_file":
            self.config.setdefault("local_file", {})["model"] = model
        else:
            self.config["local"]["model"] = model
        self.save_config()

    def load_local_gguf(self, path: str) -> bool:
        return self.local_gguf.load_model(path)

    def get_available_models(self) -> dict:
        result = {"local": [], "cloud": []}

        if self.ollama.is_available():
            for m in self.ollama.list_models():
                result["local"].append({"name": m["name"], "display": m["name"]})

        if self.cloud.is_available():
            for m in self.cloud.list_models():
                result["cloud"].append({"name": m["id"], "display": m["name"]})

        return result

    def check_connection(self, provider: str = None) -> dict:
        status = {}
        if provider is None or provider == "ollama":
            status["ollama"] = self.ollama.is_available()
        if provider is None or provider == "cloud":
            status["cloud"] = self.cloud.is_available()
        return status

    def _build_messages(self, files_content: list[dict]) -> list[dict]:
        messages = [{"role": "system", "content": self.system_prompt}]

        budget_tokens = estimate_tokens(self.system_prompt)
        max_total = self.config.get("ai", {}).get("context_tokens", 16000)

        context_limit = self.config.get("ai", {}).get("context_messages", 20)
        recent = self.conversation_history[-context_limit:]

        for msg in recent:
            text = msg.get("content", "")
            budget_tokens += estimate_tokens(text)
            if budget_tokens > max_total:
                break
            messages.append(msg)

        if files_content:
            for fc in files_content:
                messages.append({
                    "role": "user",
                    "content": f"[Archivo adjunto: {fc.get('name', 'archivo')}]\n{fc.get('content', '')}",
                })

        return messages

    def send_message(self, text: str, files_content: list[dict] = None) -> Generator[str, None, None]:
        self.conversation_history.append({"role": "user", "content": text})

        temperature = self.config.get("ai", {}).get("temperature", 0.7)
        max_tokens = self.config.get("ai", {}).get("max_tokens", 4096)

        try:
            messages = self._build_messages(files_content or [])

            if self.current_provider == "ollama":
                generator = self.ollama.chat(
                    model=self.current_model,
                    messages=messages,
                    stream=True,
                    options={"temperature": temperature},
                )
            elif self.current_provider == "local_file":
                if not self.local_gguf.is_loaded():
                    yield "Cargando modelo local... Esto puede tardar unos momentos.\n\n"
                    self.local_gguf.load_model(self.current_model)
                    yield "Modelo cargado correctamente!\n\n"
                generator = self.local_gguf.chat(
                    messages=messages,
                    temperature=temperature,
                )
            else:
                generator = self.cloud.chat(
                    model=self.current_model,
                    messages=messages,
                    stream=True,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            full_response = ""
            for chunk in generator:
                full_response += chunk
                yield chunk

            self.conversation_history.append({"role": "assistant", "content": full_response})
        except Exception:
            self.conversation_history.pop()
            raise

    def clear_history(self):
        self.conversation_history.clear()

    def is_model_ready(self) -> bool:
        if self.current_provider == "ollama":
            return self.ollama.is_available()
        elif self.current_provider == "local_file":
            return self.local_gguf.is_loaded() or os.path.exists(self.current_model)
        else:
            return self.cloud.is_available() and bool(self.cloud.api_key)