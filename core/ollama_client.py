import json
from typing import Generator, Optional

import requests

from .errors import (
    ProviderConnectionError,
    ProviderHTTPError,
    ProviderTimeout,
    with_retries,
)

DEFAULT_TIMEOUT = 120
SHORT_TIMEOUT = 5


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def is_available(self) -> bool:
        try:
            resp = self.session.get(f"{self.base_url}/api/tags", timeout=SHORT_TIMEOUT)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[dict]:
        try:
            resp = self.session.get(f"{self.base_url}/api/tags", timeout=10)
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
            raise ProviderHTTPError(resp.status_code, resp.text[:200])
        except (ProviderConnectionError, ProviderTimeout):
            return []
        except ProviderHTTPError:
            return []
        except requests.RequestException as e:
            return []

    def pull_model(self, model_name: str) -> Generator[str, None, None]:
        try:
            resp = self.session.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                stream=True,
                timeout=300,
            )
            if resp.status_code != 200:
                raise ProviderHTTPError(resp.status_code, resp.text[:200])
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    if status:
                        yield status
        except Exception as e:
            raise ProviderConnectionError(str(e)) from e

    def chat(
        self,
        model: str,
        messages: list[dict],
        stream: bool = True,
        options: Optional[dict] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Generator[str, None, None]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if options:
            payload["options"] = options

        def _request():
            return self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=stream,
                timeout=timeout,
            )

        try:
            resp = with_retries(_request)
            if resp.status_code != 200:
                raise ProviderHTTPError(resp.status_code, resp.text[:200])

            if stream:
                for line in resp.iter_lines():
                    if not line:
                        continue
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
        except ProviderHTTPError:
            raise
        except Exception as e:
            if isinstance(e, requests.Timeout):
                raise ProviderTimeout(str(e)) from e
            raise ProviderConnectionError(str(e)) from e

    def generate(
        self,
        model: str,
        prompt: str,
        stream: bool = True,
        options: Optional[dict] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Generator[str, None, None]:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }
        if options:
            payload["options"] = options

        def _request():
            return self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=stream,
                timeout=timeout,
            )

        try:
            resp = with_retries(_request)
            if resp.status_code != 200:
                raise ProviderHTTPError(resp.status_code, resp.text[:200])

            if stream:
                for line in resp.iter_lines():
                    if not line:
                        continue
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
        except ProviderHTTPError:
            raise
        except Exception as e:
            if isinstance(e, requests.Timeout):
                raise ProviderTimeout(str(e)) from e
            raise ProviderConnectionError(str(e)) from e

    def get_model_info(self, model_name: str) -> Optional[dict]:
        try:
            resp = self.session.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None