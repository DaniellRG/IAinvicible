# IA Invisible

Asistente de IA de escritorio para Windows, construido con **Python** y **PyQt6**.

Chat con modelos locales (Ollama y archivos GGUF) y modelos en la nube
(APIs compatibles con OpenAI y Anthropic), con historial persistente de
conversaciones, adjuntos de archivos, exportacion a Markdown y atajos de
teclado.

---

## Funcionalidades

### Modelos de IA
- **Ollama local**: detecta modelos instalados automaticamente y chatea en streaming.
- **Archivos GGUF locales**: busca modelos en tu PC (`.gguf`, `.bin`, `.safetensors`, ...)
  y los carga con `llama-cpp-python`.
- **Nube (OpenAI-compatible)**: GPT y cualquier API compatible (`/chat/completions`).
- **Nube (Anthropic)**: modelos Claude via `/v1/messages`.

### Chat
- Respuestas en **streaming** (token por token).
- Indicador de escritura ("...") mientras genera.
- Boton **Detener** / `Esc` para cancelar la generacion.
- Adjuntar archivos (PDF, DOCX, texto, codigo, hojas...) y **imagenes** con preview.
- Copiar respuestas de la IA con un clic.
- **Exportar** la conversacion actual a **Markdown** (`F4`), guardada en `exports/`.

### Historial
- Guardado automatico de conversaciones en `history/` (JSON).
- Panel lateral con titulo, numero de mensajes, **renombrar** y **eliminar**.
- Nueva conversacion con `F7`.

### Personalizacion
- Tema claro/oscuro (`F9`).
- Modo compacto (`F10`).
- Modo "auto-hide": oculta la ventana tras 15 s sin uso (`F8`, **desactivado por defecto**).

### Atajos de teclado

| Atajo | Accion |
|-------|--------|
| `Ctrl` + `Alt` + `Z` | Mostrar / ocultar ventana |
| `F4` | Exportar conversacion (.md) |
| `F5` | Actualizar modelos |
| `F6` | Configurar API Key |
| `F7` | Nueva conversacion |
| `F8` | Auto-hide on/off |
| `F9` | Alternar tema claro/oscuro |
| `F10` | Modo compacto |
| `Esc` | Detener generacion |

---

## Requisitos

- Windows 10/11
- Python 3.10 o superior
- (Opcional) [Ollama](https://ollama.com) con un modelo descargado para uso local

## Instalacion

### Opcion A: instalador (npm)
```bash
npm install -g iainvisible
iainvisible
```

### Opcion B: desde el codigo
```bash
cd IAinvicible
pip install -r requirements.txt
python main.py
```

> El cliente GGUF es **opcional**: si `llama-cpp-python` no esta instalado,
> la aplicacion arranca igual y solo falla al intentar usar modelos `.gguf`.

### Configuracion automatica
- `Iniciar.bat`: detecta Python, instala dependencias faltantes y arranca.
- `iainvisible.cmd`: busca `pythonw.exe` (sin consola) y lanza `main.py`.
- `launcher.py`: punto de entrada alternativo.

---

## Estructura del proyecto

```
IAinvicible/
├── main.py                  # Punto de entrada (oculta consola, arranca la UI)
├── launcher.py              # Punto de entrada alternativo
├── config.json              # Configuracion (se genera solo, no se sube al repo)
├── core/                    # Motor de IA
│   ├── ai_engine.py         # Orquesta proveedores, contexto e historial en memoria
│   ├── ollama_client.py     # Cliente de Ollama (retries, retransmision)
│   ├── cloud_client.py      # Cliente nube OpenAI-compatible / Anthropic
│   ├── local_gguf.py        # Carga de modelos GGUF (import opcional)
│   ├── errors.py            # Excepciones tipadas y helper de reintentos
│   └── anti_capture.py      # Privacidad de ventana en Windows
├── ui/                      # Interfaz PyQt6
│   ├── main_window.py       # Ventana principal, atajos, historial
│   ├── chat_widget.py       # Burbujas de chat, indicador de escritura
│   ├── input_bar.py         # Entrada de texto, adjuntos, boton detener
│   ├── model_selector.py    # Selector de modelos y buscador de archivos
│   └── styles.py            # Temas claro/oscuro
├── utils/                   # Utilidades
│   ├── chat_history.py      # Guardar/cargar/borrar conversaciones
│   ├── file_handler.py      # Leer archivos y previews de imagen
│   ├── export.py            # Exportar conversacion a Markdown
│   └── cleanup.py           # Limpieza de temporales al salir
├── history/                 # Conversaciones guardadas (JSON)
├── exports/                 # Conversaciones exportadas (.md)
└── requirements.txt         # Dependencias Python
```

---

## Configuracion (`config.json`)

El archivo se crea solo en la primera ejecucion. Secciones:

```jsonc
{
  "cloud": {
    "provider": "openai",            // "openai" | "anthropic" | "openai_compatible"
    "api_key": "",                    // tu API key (F6 para configurarla)
    "model": "gpt-4o-mini",
    "base_url": "https://api.openai.com/v1"
  },
  "local": {
    "ollama_url": "http://localhost:11434",
    "model": "llama3.2:3b"
  },
  "ai": {
    "system_prompt": "Eres un asistente util y preciso. ...",
    "temperature": 0.7,
    "max_tokens": 4096,
    "context_messages": 20,
    "context_tokens": 16000
  },
  "ui": {
    "theme": "dark",                 // "dark" | "light"
    "window_title": "Notas.txt - Bloc de notas"
  }
}
```

- `ai.system_prompt`: cambia la personalidad/instrucciones del asistente.
- `ai.temperature`: creatividad de las respuestas (0.0 - 2.0).
- `ai.context_messages` / `ai.context_tokens`: cuantos mensajes anteriores y
  cuantos tokens aproximados se envian al modelo como contexto.
- La ventana tambien guarda posicion, tamanio y tema al cerrarse.

---

## Notas tecnicas

- **Errores reales**: los clientes lanzan excepciones tipadas
  (`ProviderConnectionError`, `ProviderTimeout`, `ProviderHTTPError`) en vez de
  devolver mensajes de error como si fueran respuestas de la IA.
- **Reintentos**: ante fallos de conexion se reintenta con backoff.
- **Contexto**: el historial enviado al modelo se recorta por numero de mensajes
  *y* por tokens estimados para no exceder la ventana de contexto.
- **Robustez**: la dependencia pesada `llama-cpp-python` es opcional en tiempo
  de importacion.

## Licencia

Proyecto privado (`UNLICENSED`).