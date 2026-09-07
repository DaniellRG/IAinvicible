import os
import json
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QLabel,
    QPushButton, QFrame, QVBoxLayout, QLineEdit,
    QDialog, QListWidget, QListWidgetItem, QFileDialog,
    QSplitter, QTabWidget, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont


OLLAMA_PATHS = [
    os.path.expanduser("~\\.ollama\\models\\blobs"),
    "C:\\Users\\{}\\.ollama\\models\\blobs".format(os.getenv("USERNAME", "")),
]

OLLAMA_MANIFESTS = os.path.expanduser("~\\.ollama\\models\\manifests\\registry.ollama.ai\\library")


class OllamaScanWorker(QThread):
    finished = pyqtSignal(list)

    def run(self):
        models = set()
        manifests_dir = OLLAMA_MANIFESTS
        if os.path.exists(manifests_dir):
            try:
                for model_dir in os.listdir(manifests_dir):
                    model_path = os.path.join(manifests_dir, model_dir)
                    if os.path.isdir(model_path):
                        for tag in os.listdir(model_path):
                            full_name = f"{model_dir}:{tag}" if tag != "latest" else model_dir
                            models.add(full_name)
            except Exception:
                pass

        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000
            )
            for line in result.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if parts:
                    models.add(parts[0])
        except Exception:
            pass

        self.finished.emit(sorted(models))


class FolderScanWorker(QThread):
    finished = pyqtSignal(list)

    def __init__(self, folder: str):
        super().__init__()
        self.folder = folder

    def run(self):
        extensions = (".gguf", ".bin", ".pt", ".safetensors", ".pth", ".onnx")
        found = []
        try:
            for root, dirs, files in os.walk(self.folder):
                for f in files:
                    if f.lower().endswith(extensions):
                        full_path = os.path.join(root, f)
                        try:
                            size_mb = os.path.getsize(full_path) / (1024 * 1024)
                        except Exception:
                            size_mb = 0
                        found.append((f, full_path, size_mb))
        except Exception:
            pass
        found.sort(key=lambda x: x[0])
        self.finished.emit(found)


class ModelBrowserDialog(QDialog):
    model_selected = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buscar modelos en el PC")
        self.setMinimumSize(550, 450)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #d4d4d4; }
            QLabel { color: #d4d4d4; }
            QLineEdit {
                background-color: #3c3c3c; color: #d4d4d4;
                border: 1px solid #555; border-radius: 4px;
                padding: 8px; font-size: 12px;
            }
            QListWidget {
                background-color: #252526; color: #d4d4d4;
                border: 1px solid #555; border-radius: 4px;
                font-size: 12px;
            }
            QListWidget::item { padding: 6px 8px; }
            QListWidget::item:selected { background-color: #094771; }
            QListWidget::item:hover { background-color: #2d2d2d; }
            QPushButton {
                background-color: #3c3c3c; color: #d4d4d4;
                border: 1px solid #555; border-radius: 4px;
                padding: 8px 14px; font-size: 12px;
            }
            QPushButton:hover { background-color: #505050; }
            QTabWidget::pane { border: 1px solid #333; }
            QTabBar::tab {
                background: #252526; color: #888;
                padding: 8px 16px; margin-right: 2px;
                border: 1px solid #333; border-bottom: none;
                border-radius: 4px 4px 0 0;
            }
            QTabBar::tab:selected { background: #1e1e1e; color: #d4d4d4; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        ollama_tab = self._create_ollama_tab()
        tabs.addTab(ollama_tab, "Ollama Local")

        folder_tab = self._create_folder_tab()
        tabs.addTab(folder_tab, "Explorar Archivos")

    def _create_ollama_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)

        info = QLabel("Modelos detectados en Ollama:")
        info.setStyleSheet("font-weight: bold; color: #888;")
        layout.addWidget(info)

        self.ollama_search = QLineEdit()
        self.ollama_search.setPlaceholderText("Buscar modelo...")
        self.ollama_search.textChanged.connect(self._filter_ollama)
        layout.addWidget(self.ollama_search)

        self.ollama_list = QListWidget()
        self.ollama_list.itemDoubleClicked.connect(self._select_ollama_model)
        layout.addWidget(self.ollama_list, 1)

        btn_row = QHBoxLayout()
        rescan_btn = QPushButton("\u21bb Escanear")
        rescan_btn.clicked.connect(self._scan_ollama)
        btn_row.addWidget(rescan_btn)

        select_btn = QPushButton("Seleccionar")
        select_btn.setStyleSheet("QPushButton { background-color: #0078d4; color: white; }")
        select_btn.clicked.connect(self._select_ollama_from_button)
        btn_row.addWidget(select_btn)
        layout.addLayout(btn_row)

        QTimer.singleShot(100, self._scan_ollama)
        return widget

    def _create_folder_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)

        info = QLabel("Busca archivos de modelo (.gguf, .bin, .pt, .safetensors):")
        info.setStyleSheet("font-weight: bold; color: #888;")
        layout.addWidget(info)

        self.folder_search = QLineEdit()
        self.folder_search.setPlaceholderText("Ruta de carpeta o buscar...")
        layout.addWidget(self.folder_search)

        browse_row = QHBoxLayout()
        browse_btn = QPushButton("\U0001F4C2 Examinar carpeta")
        browse_btn.clicked.connect(self._browse_folder)
        browse_row.addWidget(browse_btn)

        search_btn = QPushButton("\U0001F50D Buscar en PC")
        search_btn.clicked.connect(self._search_pc)
        browse_row.addWidget(search_btn)
        layout.addLayout(browse_row)

        self.folder_list = QListWidget()
        self.folder_list.itemDoubleClicked.connect(self._select_folder_model)
        layout.addWidget(self.folder_list, 1)

        select_btn = QPushButton("Seleccionar")
        select_btn.setStyleSheet("QPushButton { background-color: #0078d4; color: white; }")
        select_btn.clicked.connect(self._select_folder_from_button)
        layout.addWidget(select_btn)

        return widget

    def _scan_ollama(self):
        self.ollama_list.clear()
        item = QListWidgetItem("Escaneando modelos de Ollama...")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        item.setForeground(Qt.GlobalColor.gray)
        self.ollama_list.addItem(item)

        self._ollama_worker = OllamaScanWorker()
        self._ollama_worker.finished.connect(self._on_ollama_scanned)
        self._ollama_worker.start()

    def _on_ollama_scanned(self, models: list):
        self.ollama_list.clear()
        for model in models:
            item = QListWidgetItem(f"\U0001F4BB {model}")
            item.setData(Qt.ItemDataRole.UserRole, model)
            self.ollama_list.addItem(item)

        if not models:
            item = QListWidgetItem("No se encontraron modelos. Instala modelos con: ollama pull <modelo>")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item.setForeground(Qt.GlobalColor.gray)
            self.ollama_list.addItem(item)

    def _filter_ollama(self, text: str):
        for i in range(self.ollama_list.count()):
            item = self.ollama_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def _select_ollama_model(self, item: QListWidgetItem):
        model = item.data(Qt.ItemDataRole.UserRole)
        if model:
            self.model_selected.emit("ollama", model)
            self.accept()

    def _select_ollama_from_button(self):
        item = self.ollama_list.currentItem()
        if item:
            self._select_ollama_model(item)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta con modelos")
        if folder:
            self.folder_search.setText(folder)
            self._scan_folder(folder)

    def _scan_folder(self, folder: str):
        self.folder_list.clear()
        item = QListWidgetItem("Buscando archivos de modelo...")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        item.setForeground(Qt.GlobalColor.gray)
        self.folder_list.addItem(item)

        self._folder_worker = FolderScanWorker(folder)
        self._folder_worker.finished.connect(self._on_folder_scanned)
        self._folder_worker.start()

    def _on_folder_scanned(self, found: list):
        self.folder_list.clear()
        for name, path, size in found:
            label = f"\U0001F4C4 {name}  ({size:.0f} MB)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.folder_list.addItem(item)

        if not found:
            item = QListWidgetItem("No se encontraron archivos de modelo en esta carpeta")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item.setForeground(Qt.GlobalColor.gray)
            self.folder_list.addItem(item)

    def _search_pc(self):
        search_path = self.folder_search.text().strip()
        if not search_path:
            search_path = os.path.expanduser("~")
        if not os.path.exists(search_path):
            self.folder_list.clear()
            item = QListWidgetItem("Ruta no encontrada")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item.setForeground(Qt.GlobalColor.gray)
            self.folder_list.addItem(item)
            return
        self._scan_folder(search_path)

    def _select_folder_model(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            name = os.path.basename(path)
            self.model_selected.emit("local_file", path)
            self.accept()

    def _select_folder_from_button(self):
        item = self.folder_list.currentItem()
        if item:
            self._select_folder_model(item)


class ModelSelector(QWidget):
    model_changed = pyqtSignal(str, str)
    test_connection = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("header_bar")
        self._loading = False
        self._dot_timer = QTimer()
        self._dot_timer.timeout.connect(self._animate_loading)
        self._dot_count = 0
        self._spinner_chars = ["\u25d0", "\u25d3", "\u25d1", "\u25d2"]
        self._spinner_index = 0
        self._spinner_timer = QTimer()
        self._spinner_timer.timeout.connect(self._animate_badge)
        self._badge_name = ""
        self._badge_hide_timer = QTimer()
        self._badge_hide_timer.setSingleShot(True)
        self._badge_hide_timer.timeout.connect(lambda: self.status_badge.setVisible(False))
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(14, 6, 14, 0)
        badge_row.setSpacing(6)
        self.status_badge = QLabel()
        self.status_badge.setObjectName("status_badge")
        self.status_badge.setVisible(False)
        self.status_badge.setMaximumWidth(320)
        self.status_badge.setStyleSheet("color: #d4d4d4; background: transparent; border: none;")
        badge_row.addWidget(self.status_badge)
        badge_row.addStretch()
        outer.addLayout(badge_row)

        layout = QHBoxLayout()
        layout.setContentsMargins(14, 6, 14, 8)
        layout.setSpacing(10)

        self.status_dot = QLabel("\u25cf")
        self.status_dot.setObjectName("status_dot")
        self.status_dot.setFixedWidth(22)
        layout.addWidget(self.status_dot)

        self.model_combo = QComboBox()
        self.model_combo.setObjectName("model_combo")
        self.model_combo.setMinimumWidth(240)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        layout.addWidget(self.model_combo)

        self.status_label = QLabel("Sin modelo")
        self.status_label.setObjectName("status_label")
        layout.addWidget(self.status_label)

        layout.addStretch()

        self.browse_btn = QPushButton("\U0001F50D")
        self.browse_btn.setObjectName("attach_btn")
        self.browse_btn.setFixedSize(32, 32)
        self.browse_btn.setToolTip("Buscar modelos en el PC")
        self.browse_btn.clicked.connect(self._open_browser)
        layout.addWidget(self.browse_btn)

        self.refresh_btn = QPushButton("\u21bb")
        self.refresh_btn.setObjectName("attach_btn")
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.setToolTip("Actualizar modelos de Ollama")
        self.refresh_btn.clicked.connect(self.test_connection.emit)
        layout.addWidget(self.refresh_btn)

        outer.addLayout(layout)

        self.set_status("off")

    def _filter_models(self, text: str):
        current = self.model_combo.currentText()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for model in self._all_models:
            display, provider, model_id = model
            if text.lower() in display.lower():
                self.model_combo.addItem(display, (provider, model_id))
        idx = self.model_combo.findText(current)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        self.model_combo.blockSignals(False)

    def _open_browser(self):
        dialog = ModelBrowserDialog(self)
        dialog.model_selected.connect(self._on_browse_model)
        dialog.show()
        try:
            from core.anti_capture import exclude_from_capture, set_topmost
            hwnd = int(dialog.winId())
            exclude_from_capture(hwnd)
            set_topmost(hwnd)
        except Exception:
            pass
        dialog.exec()

    def _on_browse_model(self, provider: str, model_id: str):
        display = f"\U0001F4C2 {os.path.basename(model_id)}" if provider == "local_file" else f"\U0001F4BB {model_id}"
        self._all_models.append((display, provider, model_id))
        self.model_combo.addItem(display, (provider, model_id))
        self.model_combo.setCurrentIndex(self.model_combo.count() - 1)
        self.model_changed.emit(provider, model_id)

    def _on_model_changed(self, text):
        if not text:
            return
        data = self.model_combo.currentData()
        if data:
            provider, model = data
            self.model_changed.emit(provider, model)

    def set_status(self, status: str):
        colors = {
            "ready": "#00cc66",
            "loading": "#cccc00",
            "error": "#cc3333",
            "off": "#555555"
        }
        color = colors.get(status, "#555555")
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 16px;")
        if status == "loading":
            self._loading = True
            self._dot_count = 0
            self._dot_timer.start(400)
        else:
            self._loading = False
            self._dot_timer.stop()
        if status == "ready":
            self.status_label.setText("Listo")
        elif status == "loading":
            self.status_label.setText("Cargando...")
        elif status == "error":
            self.status_label.setText("Error")
        else:
            self.status_label.setText("Sin modelo")

    def _animate_loading(self):
        self._dot_count = (self._dot_count + 1) % 4
        dots = "." * self._dot_count
        self.status_label.setText(f"Cargando{dots}")

    def _animate_badge(self):
        self._spinner_index += 1
        self._update_badge_text()

    def _update_badge_text(self):
        name = self._badge_name
        if len(name) > 26:
            name = name[:24] + "\u2026"
        spinner = self._spinner_chars[self._spinner_index % len(self._spinner_chars)]
        if name:
            self.status_badge.setText(f"{spinner}  Cargando modelo\u2026 {name}")
        else:
            self.status_badge.setText(f"{spinner}  Cargando modelo\u2026")

    def show_gguf_loading(self, name: str = ""):
        self._badge_name = name
        self._badge_hide_timer.stop()
        self.status_badge.setVisible(True)
        self.status_badge.setStyleSheet("""
            QLabel {
                background: rgba(255, 193, 7, 0.12);
                color: #ffc107;
                border: 1px solid rgba(255, 193, 7, 0.55);
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 10px;
                font-weight: 600;
            }
        """)
        self._spinner_timer.start(160)
        self._update_badge_text()

    def show_gguf_ready(self, name: str = ""):
        self._spinner_timer.stop()
        self._badge_name = name
        self.status_badge.setVisible(True)
        self.status_badge.setStyleSheet("""
            QLabel {
                background: rgba(0, 204, 102, 0.14);
                color: #00cc66;
                border: 1px solid rgba(0, 204, 102, 0.6);
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 10px;
                font-weight: 600;
            }
        """)
        self.status_badge.setText("\u2713 Modelo listo")
        self._badge_hide_timer.start(3500)

    def show_gguf_error(self, msg: str = ""):
        self._spinner_timer.stop()
        self._badge_name = msg
        self.status_badge.setVisible(True)
        self.status_badge.setStyleSheet("""
            QLabel {
                background: rgba(204, 51, 51, 0.14);
                color: #ff6b6b;
                border: 1px solid rgba(204, 51, 51, 0.6);
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 10px;
                font-weight: 600;
            }
        """)
        self.status_badge.setText("\u2715 Error al cargar modelo")
        self._badge_hide_timer.start(6000)

    def add_model(self, display_name: str, provider: str, model_id: str):
        if not hasattr(self, '_all_models'):
            self._all_models = []
        self._all_models.append((display_name, provider, model_id))
        self.model_combo.addItem(display_name, (provider, model_id))

    def clear_models(self):
        self.model_combo.clear()
        self._all_models = []

    def set_current_model(self, provider: str, model_id: str):
        for i in range(self.model_combo.count()):
            data = self.model_combo.itemData(i)
            if data and data[0] == provider and data[1] == model_id:
                self.model_combo.setCurrentIndex(i)
                return

    def current_model(self):
        data = self.model_combo.currentData()
        if data:
            return data[0], data[1]
        return None, None

    def stop_timers(self):
        self._dot_timer.stop()
        self._spinner_timer.stop()
        self._badge_hide_timer.stop()


import os
