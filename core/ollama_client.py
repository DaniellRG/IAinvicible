import requests
import json
from typing import Generator, Optional


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def is_available(self) -> bool:
        try:
            resp = self.session.get(f"{self.base_url}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[dict]:
        try:
            resp = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("models", []):
                    models.append({
                        "name": m.get("name", ""),
                        "size": m.get("size", 0),
                        "modified": m.get("modified_at", ""),
                    })
                return models
            return []
        except Exception:
            return []

    def pull_model(self, model_name: str) -> Generator[str, None, None]:
        try:
            resp = self.session.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                stream=True,
                timeout=300
            )
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    yield status
        except Exception as e:
            yield f"Error: {str(e)}"

    def chat(self, model: str, messages: list[dict], stream: bool = True) -> Generator[str, None, None]:
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": stream
            }
            resp = self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=stream,
                timeout=120
            )
            if stream:
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        done = data.get("done", False)
                        if content:
                            yield content
                        if done:
                            return
            else:
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                yield content
        except Exception as e:
            yield f"Error de conexion con Ollama: {str(e)}"

    def generate(self, model: str, prompt: str, stream: bool = True) -> Generator[str, None, None]:
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream
            }
            resp = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=stream,
                timeout=120
            )
            if stream:
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        content = data.get("response", "")
                        done = data.get("done", False)
                        if content:
                            yield content
                        if done:
                            return
            else:
                data = resp.json()
                yield data.get("response", "")
        except Exception as e:
            yield f"Error de conexion con Ollama: {str(e)}"

    def get_model_info(self, model_name: str) -> Optional[dict]:
        try:
            resp = self.session.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None
