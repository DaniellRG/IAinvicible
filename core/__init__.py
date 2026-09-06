"""Nucleo del motor de IA: clientes de proveedores y motor central.

- ai_engine: orquesta proveedores, contexto e historial.
- ollama_client / cloud_client / local_gguf: clientes de modelos.
- errors: excepciones tipadas y reintentos.
- anti_capture: configuracion de privacidad de la ventana en Windows.
"""