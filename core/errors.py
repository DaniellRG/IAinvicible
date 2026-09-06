import time

import httpx
import requests


class AIProviderError(Exception):
    """Error base de un proveedor de IA (Ollama, nube, GGUF)."""


class ProviderConnectionError(AIProviderError):
    """No se pudo conectar con el proveedor."""


class ProviderTimeout(AIProviderError):
    """El proveedor no respondio a tiempo."""


class ProviderHTTPError(AIProviderError):
    """El proveedor respondio con un estado HTTP de error."""

    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        super().__init__(f"Error del proveedor ({status_code}): {detail}")


_CONNECTION_ERRORS = (
    requests.ConnectionError,
    requests.Timeout,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.TimeoutException,
)


def is_connection_error(exc: Exception) -> bool:
    return isinstance(exc, _CONNECTION_ERRORS)


def with_retries(fn, retries: int = 2, delay: float = 1.0):
    """Ejecuta fn() reintentando ante errores de conexion."""
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:
            if not is_connection_error(exc) or attempt >= retries:
                raise
            attempt += 1
            time.sleep(delay * attempt)