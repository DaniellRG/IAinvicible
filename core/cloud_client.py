import json
from typing import Generator, Optional

import httpx

from .errors import (
    ProviderConnectionError,
    ProviderHTTPError,
    ProviderTimeout,
    with_retries,
)

DEFAULT_TIMEOUT = 120
SHORT_TIMEOUT = 10

KNOWN_PROVIDERS = ("openai", "anthropic", "gemini", "openai_compatible")


class CloudClient:
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        provider: str = "openai",
    ):
        self.api_key = api_key
        self.provider = provider
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=SHORT_TIMEOUT, follow_redirects=True)
        self._set_headers()

    def _set_headers(self):
        base_headers = {"Content-Type": "application/json"}
        if self.api_key:
            if self.provider == "anthropic":
                base_headers.update({
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "anthropic-dangerous-direct-browser-access": "true",
                })
            else:
                base_headers["Authorization"] = f"Bearer {self.api_key}"
        self.headers = base_headers

    def set_api_key(self, key: str):
        self.api_key = key
        self._set_headers()

    def set_provider(self, provider: str, base_url: str):
        self.provider = provider
        self._base_url = base_url.rstrip("/")
        self._set_headers()

    @property
    def base_url(self) -> str:
        return self._base_url

    def _chat_endpoint(self) -> str:
        if self.provider == "anthropic":
            return f"{self._base_url}/v1/messages"
        return f"{self._base_url}/chat/completions"

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            path = "/v1/models" if self.provider == "anthropic" else "/models"
            resp = self._client.get(f"{self._base_url}{path}", headers=self.headers)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[dict]:
        if not self.api_key:
            return []
        try:
            path = "/v1/models" if self.provider == "anthropic" else "/models"
            resp = self._client.get(f"{self._base_url}{path}", headers=self.headers)
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("data", []):
                    model_id = m.get("id", "")
                    if any(x in model_id for x in ["gpt", "claude", "gemini", "o1", "o3", "mistral", "llama"]):
                        models.append({"id": model_id, "name": model_id})
                return models
            return []
        except Exception:
            return []

    def chat(
        self,
        model: str,
        messages: list[dict],
        stream: bool = True,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Generator[str, None, None]:
        try:
            if self.provider == "anthropic":
                yield from self._chat_anthropic(model, messages, streaming=stream, temperature=temperature, max_tokens=max_tokens, timeout=timeout)
            else:
                yield from self._chat_openai_compatible(model, messages, stream=stream, temperature=temperature, max_tokens=max_tokens, timeout=timeout)
        except ProviderHTTPError as e:
            raise
        except ProviderTimeout as e:
            raise
        except httpx.TimeoutException as e:
            raise ProviderTimeout(str(e)) from e
        except httpx.TransportError as e:
            raise ProviderConnectionError(str(e)) from e

    def _chat_openai_compatible(
        self,
        model: str,
        messages: list[dict],
        stream: bool,
        temperature: Optional[float],
        max_tokens: int,
        timeout: float,
    ) -> Generator[str, None, None]:
        payload = {"model": model, "messages": messages, "stream": stream}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens:
            payload["max_tokens"] = max_tokens

        url = f"{self._base_url}/chat/completions"

        def _request():
            self._client.timeout = httpx.Timeout(timeout)
            req = self._client.build_request("POST", url, json=payload, headers=self.headers)
            return self._client.send(req, stream=stream)

        resp = with_retries(_request)
        if resp.status_code != 200:
            error_body = resp.read().decode(errors="replace")
            raise ProviderHTTPError(resp.status_code, error_body[:200])

        if not stream:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                yield content
            return

        with resp as r:
            for line in r.iter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    return
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                delta = data.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content

    def _chat_anthropic(
        self,
        model: str,
        messages: list[dict],
        streaming: bool,
        temperature: Optional[float],
        max_tokens: int,
        timeout: float,
    ) -> Generator[str, None, None]:
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        system = "\n".join(system_parts) if system_parts else None
        chat_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") in ("user", "assistant")
        ]

        payload = {"model": model, "messages": chat_messages, "stream": streaming}
        if system:
            payload["system"] = system
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens:
            payload["max_tokens"] = max_tokens

        url = f"{self._base_url}/v1/messages"

        def _request():
            self._client.timeout = httpx.Timeout(timeout)
            req = self._client.build_request("POST", url, json=payload, headers=self.headers)
            return self._client.send(req, stream=streaming)

        resp = with_retries(_request)
        if resp.status_code != 200:
            error_body = resp.read().decode(errors="replace")
            raise ProviderHTTPError(resp.status_code, error_body[:200])

        if not streaming:
            data = resp.json()
            content = "".join(
                block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
            )
            if content:
                yield content
            return

        with resp as r:
            for line in r.iter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    return
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "content_block_delta":
                    delta = data.get("delta", {})
                    text = delta.get("text", "")
                    if text:
                        yield text

    def chat_sync(
        self,
        model: str,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
    ) -> str:
        parts = []
        for chunk in self.chat(
            model=model,
            messages=messages,
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            parts.append(chunk)
        return "".join(parts)

    def close(self):
        try:
            self._client.close()
        except Exception:
            pass

    def __del__(self):
        self.close()