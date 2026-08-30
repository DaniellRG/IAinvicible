import os
from typing import Generator, Optional
from llama_cpp import Llama


class LocalGGUFClient:
    def __init__(self):
        self.model: Optional[Llama] = None
        self.model_path: str = ""
        self._loading = False

    def load_model(self, path: str, n_ctx: int = 4096, n_gpu_layers: int = 0) -> bool:
        if not os.path.exists(path):
            return False

        self.model_path = path
        self._loading = True

        try:
            self.model = Llama(
                model_path=path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                n_threads=os.cpu_count() or 4,
                verbose=False
            )
            self._loading = False
            return True
        except Exception as e:
            self._loading = False
            self.model = None
            return False

    def is_loaded(self) -> bool:
        return self.model is not None

    def is_loading(self) -> bool:
        return self._loading

    def unload_model(self):
        if self.model:
            del self.model
            self.model = None
            self.model_path = ""

    def chat(self, messages: list[dict], max_tokens: int = 2048) -> Generator[str, None, None]:
        if not self.model:
            yield "Error: No hay modelo cargado."
            return

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
                temperature=0.7,
                top_p=0.9
            )

            for chunk in output:
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content

        except Exception as e:
            yield f"Error al generar respuesta: {str(e)}"

    def generate(self, prompt: str, max_tokens: int = 1024) -> Generator[str, None, None]:
        if not self.model:
            yield "Error: No hay modelo cargado."
            return

        try:
            output = self.model(
                prompt,
                max_tokens=max_tokens,
                stream=True,
                temperature=0.7,
                top_p=0.9,
                echo=False
            )

            for chunk in output:
                text = chunk.get("choices", [{}])[0].get("text", "")
                if text:
                    yield text

        except Exception as e:
            yield f"Error al generar respuesta: {str(e)}"

    def get_model_info(self) -> dict:
        if not self.model:
            return {"loaded": False}
        return {
            "loaded": True,
            "path": self.model_path,
            "name": os.path.basename(self.model_path),
            "size_gb": os.path.getsize(self.model_path) / (1024**3)
        }
