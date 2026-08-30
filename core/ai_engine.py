import json
import os
from typing import Generator, Optional
from .ollama_client import OllamaClient
from .cloud_client import CloudClient
from .local_gguf import LocalGGUFClient


CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")


class AIEngine:
    def __init__(self):
        self.config = self._load_config()
        self.ollama = OllamaClient(
            base_url=self.config.get("local", {}).get("ollama_url", "http://localhost:11434")
        )
        self.cloud = CloudClient(
            api_key=self.config.get("cloud", {}).get("api_key", ""),
            base_url=self.config.get("cloud", {}).get("base_url", "https://api.openai.com/v1"),
            provider=self.config.get("cloud", {}).get("provider", "openai")
        )
        self.local_gguf = LocalGGUFClient()
        self.current_provider = "ollama"
        self.current_model = self.config.get("local", {}).get("model", "")
        self.conversation_history: list[dict] = []
        self.system_prompt = (
            "Eres un asistente util y preciso. Responde de forma clara y concisa. "
            "Si te piden resolver un ejercicio o problema, muestra el razonamiento paso a paso. "
            "Responde en el idioma que te hablen."
        )

    def _load_config(self) -> dict:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "cloud": {"provider": "openai", "api_key": "", "model": "gpt-4o-mini", "base_url": "https://api.openai.com/v1"},
                "local": {"ollama_url": "http://localhost:11434", "model": "llama3.2:3b"},
                "ui": {"window_title": "Notas.txt - Bloc de notas", "theme": "dark", "font_size": 13}
            }

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

    def set_model(self, provider: str, model: str):
        if self.current_provider == "local_file" and provider != "local_file":
            self.local_gguf.unload_model()
        self.current_provider = provider
        self.current_model = model

    def load_local_gguf(self, path: str) -> bool:
        return self.local_gguf.load_model(path)

    def get_available_models(self) -> dict:
        result = {"local": [], "cloud": []}

        if self.ollama.is_available():
            for m in self.ollama.list_models():
                result["local"].append({
                    "name": m["name"],
                    "display": m["name"],
                })

        if self.cloud.is_available():
            for m in self.cloud.list_models():
                result["cloud"].append({
                    "name": m["id"],
                    "display": m["name"],
                })

        return result

    def check_connection(self, provider: str = None) -> dict:
        status = {}
        if provider is None or provider == "ollama":
            status["ollama"] = self.ollama.is_available()
        if provider is None or provider == "cloud":
            status["cloud"] = self.cloud.is_available()
        return status

    def send_message(self, text: str, files_content: list[dict] = None) -> Generator[str, None, None]:
        self.conversation_history.append({"role": "user", "content": text})

        messages = [{"role": "system", "content": self.system_prompt}]

        for msg in self.conversation_history[-20:]:
            messages.append(msg)

        if files_content:
            for fc in files_content:
                messages.append({
                    "role": "user",
                    "content": f"[Archivo adjunto: {fc.get('name', 'archivo')}]\n{fc.get('content', '')}"
                })

        if self.current_provider == "ollama":
            generator = self.ollama.chat(
                model=self.current_model,
                messages=messages,
                stream=True
            )
        elif self.current_provider == "local_file":
            if not self.local_gguf.is_loaded():
                yield "Cargando modelo local... Esto puede tardar unos momentos.\n\n"
                loaded = self.local_gguf.load_model(self.current_model)
                if not loaded:
                    yield "Error: No se pudo cargar el modelo GGUF. Verifica que el archivo sea valido."
                    self.conversation_history.pop()
                    return
                yield "Modelo cargado correctamente!\n\n"

            generator = self.local_gguf.chat(messages=messages)
        else:
            generator = self.cloud.chat(
                model=self.current_model,
                messages=messages,
                stream=True
            )

        full_response = ""
        for chunk in generator:
            full_response += chunk
            yield chunk

        self.conversation_history.append({"role": "assistant", "content": full_response})

    def clear_history(self):
        self.conversation_history.clear()

    def is_model_ready(self) -> bool:
        if self.current_provider == "ollama":
            return self.ollama.is_available()
        elif self.current_provider == "local_file":
            return self.local_gguf.is_loaded() or os.path.exists(self.current_model)
        else:
            return self.cloud.is_available() and bool(self.cloud.api_key)
