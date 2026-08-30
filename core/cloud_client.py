import httpx
import json
from typing import Generator, Optional


class CloudClient:
    def __init__(self, api_key: str = "", base_url: str = "https://api.openai.com/v1", provider: str = "openai"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.provider = provider
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def set_api_key(self, key: str):
        self.api_key = key
        self.headers["Authorization"] = f"Bearer {key}"

    def set_provider(self, provider: str, base_url: str):
        self.provider = provider
        self.base_url = base_url.rstrip("/")

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(f"{self.base_url}/models", headers=self.headers)
                return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[dict]:
        if not self.api_key:
            return []
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(f"{self.base_url}/models", headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    models = []
                    for m in data.get("data", []):
                        model_id = m.get("id", "")
                        if any(x in model_id for x in ["gpt", "claude", "gemini", "o1", "o3"]):
                            models.append({
                                "id": model_id,
                                "name": model_id,
                            })
                    return models
                return []
        except Exception:
            return []

    def chat(self, model: str, messages: list[dict], stream: bool = True) -> Generator[str, None, None]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "max_tokens": 4096
        }
        try:
            with httpx.Client(timeout=120) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self.headers
                ) as resp:
                    if resp.status_code != 200:
                        error_body = resp.read().decode()
                        yield f"Error API ({resp.status_code}): {error_body[:200]}"
                        return

                    for line in resp.iter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            return
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError:
            yield "Error: No se pudo conectar con la API. Verifica tu conexion a internet."
        except httpx.TimeoutException:
            yield "Error: Tiempo de espera agotado. La API no responde."
        except Exception as e:
            yield f"Error: {str(e)}"

    def chat_sync(self, model: str, messages: list[dict]) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "max_tokens": 4096
        }
        try:
            with httpx.Client(timeout=120) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self.headers
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return f"Error API ({resp.status_code})"
        except Exception as e:
            return f"Error: {str(e)}"
