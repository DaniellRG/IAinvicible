import os
from typing import Optional
from PyQt6.QtGui import QPixmap


def read_file_content(filepath: str) -> Optional[dict]:
    ext = os.path.splitext(filepath)[1].lower()
    name = os.path.basename(filepath)

    try:
        if ext in (".txt", ".csv", ".json", ".xml", ".py", ".js", ".html", ".css", ".md", ".log", ".ini", ".cfg"):
            return _read_text(filepath, name)
        elif ext == ".pdf":
            return _read_pdf(filepath, name)
        elif ext in (".docx", ".doc"):
            return _read_docx(filepath, name)
        elif ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
            return {"name": name, "content": "[Imagen adjunta]", "type": "image", "path": filepath}
        else:
            return _read_text(filepath, name)
    except Exception as e:
        return {"name": name, "content": f"[Error leyendo archivo: {str(e)}]", "type": "error"}


def _read_text(filepath: str, name: str) -> dict:
    encodings = ["utf-8", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                content = f.read()
            if len(content) > 8000:
                content = content[:8000] + "\n\n[... archivo truncado ...]"
            return {"name": name, "content": content, "type": "text"}
        except UnicodeDecodeError:
            continue
    return {"name": name, "content": "[No se pudo leer el archivo]", "type": "error"}


def _read_pdf(filepath: str, name: str) -> dict:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages[:10]:
            text += page.extract_text() or ""
        if len(text) > 8000:
            text = text[:8000] + "\n\n[... archivo truncado ...]"
        return {"name": name, "content": text, "type": "pdf"}
    except ImportError:
        return {"name": name, "content": "[PyPDF2 no instalado]", "type": "error"}
    except Exception as e:
        return {"name": name, "content": f"[Error leyendo PDF: {str(e)}]", "type": "error"}


def _read_docx(filepath: str, name: str) -> dict:
    try:
        from docx import Document
        doc = Document(filepath)
        text = "\n".join([p.text for p in doc.paragraphs[:200]])
        if len(text) > 8000:
            text = text[:8000] + "\n\n[... archivo truncado ...]"
        return {"name": name, "content": text, "type": "docx"}
    except ImportError:
        return {"name": name, "content": "[python-docx no instalado]", "type": "error"}
    except Exception as e:
        return {"name": name, "content": f"[Error leyendo DOCX: {str(e)}]", "type": "error"}


def get_image_preview(filepath: str, max_size: int = 300) -> Optional[QPixmap]:
    pixmap = QPixmap(filepath)
    if pixmap.isNull():
        return None
    return pixmap.scaled(
        max_size, max_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )


from PyQt6.QtCore import Qt
