import os
from typing import Generator, Optional

from .errors import AIProviderError

try:
    from llama_cpp import Llama
    _HAS_LLAMA_CPP = True
except ImportError:
    Llama = None
    _HAS_LLAMA_CPP = False


class GGUFNotAvailable(AIProviderError):
    """llama-cpp-python no esta instalado."""

    def __init__(self):
        super().__init__(
            "La extension GGUF no esta disponible: instala 'llama-cpp-python' "
            "para usar modelos locales (.gguf)."
        )


def llama_available() -> bool:
    return _HAS_LLAMA_CPP


class LocalGGUFClient:
    def __init__(self):
        self.model: Optional[object] = None
        self.model_path: str = ""
        self._loading = False

    def load_model(self, path: str, n_ctx: int = 4096, n_gpu_layers: int = 0) -> bool:
        if not _HAS_LLAMA_CPP:
            raise GGUFNotAvailable()
        if not os.path.exists(path):
            raise AIProviderError(f"No se encontro el archivo de modelo: {path}")

        self.model_path = path
        self._loading = True

        try:
            self.model = Llama(
                model_path=path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                n_threads=os.cpu_count() or 4,
                verbose=False,
            )
            self._loading = False
            return True
        except Exception as e:
            self._loading = False
            self.model = None
            self.model_path = ""
            raise AIProviderError(f"No se pudo cargar el modelo GGUF: {e}") from e

    def is_loaded(self) -> bool:
        return self.model is not None

    def is_loading(self) -> bool:
        return self._loading

    def unload_model(self):
        if self.model:
            del self.model
            self.model = None
            self.model_path = ""

    def _ensure_loaded(self):
        if not _HAS_LLAMA_CPP:
            raise GGUFNotAvailable()
        if not self.model:
            raise AIProviderError("No hay un modelo GGUF cargado.")

    def chat(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> Generator[str, None, None]:
        self._ensure_loaded()

        try:
            formatted = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                formatted.append({"role": role, "content": content})

            output = self.model.create_chat_completion(
                messages=formatted,
                max_tokens=max_tokens,
                stream=True,
                temperature=temperature,
                top_p=top_p,
            )

            for chunk in output:
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
        except AIProviderError:
            raise
        except Exception as e:
            raise AIProviderError(f"Error al generar respuesta: {e}") from e

    def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> Generator[str, None, None]:
        self._ensure_loaded()

        try:
            output = self.model(
                prompt,
                max_tokens=max_tokens,
                stream=True,
                temperature=temperature,
                top_p=top_p,
                echo=False,
            )

            for chunk in output:
                text = chunk.get("choices", [{}])[0].get("text", "")
                if text:
                    yield text
        except AIProviderError:
            raise
        except Exception as e:
            raise AIProviderError(f"Error al generar respuesta: {e}") from e

    def get_model_info(self) -> dict:
        if not self.model:
            return {"loaded": False}
        return {
            "loaded": True,
            "path": self.model_path,
            "name": os.path.basename(self.model_path),
            "size_gb": os.path.getsize(self.model_path) / (1024**3),
        }