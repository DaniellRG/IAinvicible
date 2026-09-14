import sys
import os
import ctypes
import ctypes.wintypes
import json
import time

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QLabel, QMessageBox, QDialog,
    QLineEdit, QFormLayout, QPushButton, QComboBox, QApplication,
    QListWidget, QListWidgetItem, QFrame, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import QAbstractNativeEventFilter

from ui.model_selector import ModelSelector
from ui.chat_widget import ChatWidget
from ui.input_bar import InputBar
from ui.prompts_panel import PromptsPanel
from ui.icon_helpers import IconButton, GRAY, BLUE, DANGER
from ui.styles import get_theme
from core.anti_capture import (
    exclude_from_capture, is_excluded_from_capture, set_topmost,
    setup_stealth_window, register_hotkey, unregister_hotkey,
    restore_capture, HOTKEY_ID_TOGGLE, WM_HOTKEY,
    hide_from_processes, spoof_process_visibility
)
from core.ai_engine import AIEngine
from utils.file_handler import read_file_content
from utils.chat_history import (
    save_conversation, load_conversation, list_conversations,
    delete_conversation, generate_title
)


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.wintypes.HWND),
        ("message", ctypes.wintypes.UINT),
        ("wParam", ctypes.wintypes.WPARAM),
        ("lParam", ctypes.wintypes.LPARAM),
        ("time", ctypes.wintypes.DWORD),
        ("pt", ctypes.wintypes.POINT),
    ]


class HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            try:
                msg = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
                if msg.message == 0x0312:
                    self.callback()
                    return True, 0
            except Exception:
                pass
        return False, 0


class AIWorker(QThread):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, engine: AIEngine, message: str, files: list = None):
        super().__init__()
        self.engine = engine
        self.message = message
        self.files = files or []

    def run(self):
        try:
            for chunk in self.engine.send_message(self.message, self.files):
                if self.isInterruptionRequested():
                    self.finished.emit()
                    return
                self.chunk_received.emit(chunk)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class ModelLoadWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, engine: AIEngine):
        super().__init__()
        self.engine = engine

    def run(self):
        try:
            models = self.engine.get_available_models()
            self.finished.emit(models)
        except Exception as e:
            self.error.emit(str(e))


class GGUFLoadWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, engine: AIEngine, path: str):
        super().__init__()
        self.engine = engine
        self.path = path

    def run(self):
        try:
            ok = self.engine.load_local_gguf(self.path)
            if ok:
                self.finished.emit()
            else:
                self.error.emit("El modelo no pudo cargarse.")
        except Exception as e:
            self.error.emit(str(e))


class ApiKeyDialog(QDialog):
    _PROVIDER_PRESETS = [
        ("OpenAI", "openai", "https://api.openai.com/v1", "gpt-4o-mini"),
        ("OpenRouter", "openai", "https://openrouter.ai/api/v1", "openai/gpt-4o-mini"),
        ("Anthropic", "anthropic", "https://api.anthropic.com", "claude-3-5-sonnet-20241022"),
        ("Personalizado", "openai_compatible", "", ""),
    ]

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar API Key")
        self.setMinimumWidth(420)
        self._engine = engine
        cloud = engine.config.get("cloud", {})
        self._saved_keys: list[dict] = list(cloud.get("saved_keys") or [])
        self._active_key_name: str = cloud.get("active_key_name", "")
        self._setup_ui()
        self._load_current(cloud)

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #d4d4d4; }
            QLabel { color: #d4d4d4; }
            QLineEdit, QComboBox {
                background-color: #3c3c3c; color: #d4d4d4;
                border: 1px solid #555; border-radius: 4px;
                padding: 8px; font-size: 12px;
            }
            QComboBox::drop-down { subcontrol-origin: padding; width: 24px; }
            QComboBox QAbstractItemView { background-color: #3c3c3c; color: #d4d4d4; }
            QPushButton {
                background-color: #555; color: #d4d4d4;
                border: none; border-radius: 4px;
                padding: 8px 12px; font-weight: 600;
            }
            QPushButton:hover { background-color: #666; }
            QPushButton#primary { background-color: #0078d4; color: white; }
            QPushButton#primary:hover { background-color: #1a8ae8; }
            QPushButton#danger { background-color: #991b1b; color: #fca5a5; }
            QPushButton#danger:hover { background-color: #b91c1c; }
            QPushButton#clear { background-color: transparent; color: #6b7a90; }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Proveedor:"))
        self.provider_combo = QComboBox()
        for label, _, _, _ in self._PROVIDER_PRESETS:
            self.provider_combo.addItem(label)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        layout.addWidget(self.provider_combo)

        self.url_wrap = QVBoxLayout()
        url_title = QLabel("URL base (ej: https://api.tuservicio.com/v1):")
        url_title.setObjectName("url_title")
        self.url_wrap.addWidget(url_title)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://...")
        self.url_wrap.addWidget(self.url_input)
        layout.addLayout(self.url_wrap)

        sep = QLabel("Keys guardadas:")
        sep.setStyleSheet("color: #6b7a90; font-size: 11px; margin-top: 6px;")
        layout.addWidget(sep)
        keys_row = QHBoxLayout()
        self.keys_combo = QComboBox()
        self.keys_combo.currentIndexChanged.connect(self._on_key_selection_changed)
        keys_row.addWidget(self.keys_combo, 1)
        self.delete_key_btn = QPushButton("Eliminar")
        self.delete_key_btn.setObjectName("danger")
        self.delete_key_btn.setFixedWidth(80)
        self.delete_key_btn.setEnabled(False)
        self.delete_key_btn.clicked.connect(self._delete_selected_key)
        keys_row.addWidget(self.delete_key_btn)
        layout.addLayout(keys_row)

        layout.addWidget(QLabel("API Key:"))
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("sk-... / sk-ant-...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.key_input)

        self.toggle_btn = QPushButton("Mostrar")
        self.toggle_btn.setFixedWidth(100)
        self.toggle_btn.setObjectName("clear")
        self.toggle_btn.clicked.connect(self._toggle_visibility)
        layout.addWidget(self.toggle_btn)

        btn_row = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        btn_row.addStretch()
        save = QPushButton("Guardar y aplicar")
        save.setObjectName("primary")
        save.clicked.connect(self.accept)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _load_current(self, cloud):
        active_name = cloud.get("active_key_name", "")
        active_provider = cloud.get("provider", "openai")
        self.keys_combo.blockSignals(True)
        self.keys_combo.addItem("(nueva key)")
        for entry in self._saved_keys:
            self.keys_combo.addItem(entry.get("name", "Sin nombre"))
        if active_name:
            idx = next((i + 1 for i, e in enumerate(self._saved_keys) if e.get("name") == active_name), 0)
            self.keys_combo.setCurrentIndex(idx)
            if idx > 0:
                self._populate_from_saved(self._saved_keys[idx - 1])
            else:
                self._set_provider_by_type(active_provider)
                self.key_input.setText(cloud.get("api_key", ""))
        else:
            self.keys_combo.setCurrentIndex(0)
            self._set_provider_by_type(active_provider)
            self.key_input.setText(cloud.get("api_key", ""))
        self.keys_combo.blockSignals(False)
        self.delete_key_btn.setEnabled(0 < self.keys_combo.currentIndex() <= len(self._saved_keys))

    def _set_provider_by_type(self, provider_type: str):
        for idx, (_, ptype, _, _) in enumerate(self._PROVIDER_PRESETS):
            if ptype == provider_type:
                self.provider_combo.setCurrentIndex(idx)
                self._on_provider_changed(idx)
                return
        self.provider_combo.setCurrentIndex(3)
        self._on_provider_changed(3)

    def _on_provider_changed(self, index: int):
        is_custom = self._PROVIDER_PRESETS[index][1] == "openai_compatible"
        for i in range(self.url_wrap.count()):
            w = self.url_wrap.itemAt(i).widget()
            if w:
                w.setVisible(is_custom)
        if is_custom and not self.url_input.text():
            base = self._engine.config.get("cloud", {}).get("base_url", "")
            if base:
                self.url_input.setText(base)

    def _populate_from_saved(self, entry: dict):
        self._set_provider_by_type(entry.get("provider", "openai"))
        self.key_input.setText(entry.get("api_key", ""))
        if entry.get("provider") == "openai_compatible":
            self.url_input.setText(entry.get("base_url", ""))

    def _on_key_selection_changed(self, index: int):
        self.delete_key_btn.setEnabled(0 < index <= len(self._saved_keys))
        if index == 0:
            cloud = self._engine.config.get("cloud", {})
            self._set_provider_by_type(cloud.get("provider", "openai"))
            self.key_input.setText(cloud.get("api_key", ""))
        else:
            self._populate_from_saved(self._saved_keys[index - 1])

    def _delete_selected_key(self):
        idx = self.keys_combo.currentIndex()
        if idx <= 0 or idx > len(self._saved_keys):
            return
        name = self._saved_keys[idx - 1].get("name", "")
        if QMessageBox.question(
            self, "Eliminar key",
            f"Eliminar \"{name}\" de las keys guardadas?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        self._saved_keys.pop(idx - 1)
        self.keys_combo.removeItem(idx)
        self._engine.config["cloud"]["saved_keys"] = self._saved_keys
        if self._active_key_name == name:
            self._active_key_name = ""
            self._engine.config["cloud"]["active_key_name"] = ""
        self.keys_combo.setCurrentIndex(0)

    def _toggle_visibility(self):
        if self.key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setText("Ocultar")
        else:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setText("Mostrar")

    def _generate_name(self, provider_type: str) -> str:
        count = sum(1 for k in self._saved_keys if k.get("provider") == provider_type)
        labels = {"openai": "OpenAI", "anthropic": "Anthropic", "openai_compatible": "Custom"}
        base = labels.get(provider_type, provider_type.title())
        return f"{base} {count + 1}"

    def accept(self):
        idx = self.keys_combo.currentIndex()
        preset_idx = self.provider_combo.currentIndex()
        _, provider_type, base_url, model = self._PROVIDER_PRESETS[preset_idx]
        api_key = self.key_input.text().strip()

        if not api_key:
            QMessageBox.warning(self, "API Key", "Debes ingresar una API Key.")
            return

        if provider_type == "openai_compatible":
            base_url = self.url_input.text().strip()

        self._engine.set_cloud_provider(provider_type, base_url)
        self._engine.set_api_key(api_key)
        self._engine.config["cloud"]["model"] = model

        name = self._generate_name(provider_type)
        entry = {
            "name": name,
            "provider": provider_type,
            "base_url": base_url,
            "model": model,
            "api_key": api_key,
        }

        if idx == 0:
            self._saved_keys.append(entry)
            self._active_key_name = name
        else:
            old_name = self._saved_keys[idx - 1].get("name", "")
            self._saved_keys[idx - 1].update(entry)
            self._saved_keys[idx - 1]["name"] = old_name
            self._active_key_name = old_name

        self._engine.config["cloud"]["saved_keys"] = self._saved_keys
        self._engine.config["cloud"]["active_key_name"] = self._active_key_name
        self._engine.save_config()
        super().accept()


class HistoryItemWidget(QWidget):
    clicked = pyqtSignal(str)
    delete_clicked = pyqtSignal(str)
    rename_clicked = pyqtSignal(str)

    def __init__(self, conv_id: str, title: str, msg_count: int, parent=None):
        super().__init__(parent)
        self._conv_id = conv_id
        self._is_selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 8, 8)
        layout.setSpacing(6)

        icon = QLabel("\U0001F4AC")
        icon.setStyleSheet("font-size: 14px; border: none; background: transparent;")
        icon.setFixedWidth(22)
        layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("font-size: 12px; border: none; font-weight: 500;")
        self._title_label.setWordWrap(True)
        text_layout.addWidget(self._title_label)

        self._count_label = QLabel(f"{msg_count} mensajes")
        self._count_label.setStyleSheet("font-size: 10px; color: #6b7a90; border: none;")
        text_layout.addWidget(self._count_label)

        layout.addLayout(text_layout, 1)

        self._rename_btn = IconButton("mdi.pencil-outline", tooltip="Renombrar", size=24)
        self._rename_btn.clicked.connect(lambda: self.rename_clicked.emit(self._conv_id))
        layout.addWidget(self._rename_btn)

        self._delete_btn = IconButton("mdi.trash-can-outline", tooltip="Eliminar", size=24,
                                      variant="danger", hover_color=DANGER)
        self._delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self._conv_id))
        layout.addWidget(self._delete_btn)

    def set_selected(self, selected: bool):
        self._is_selected = selected
        if selected:
            self.setStyleSheet("""
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #1d4ed8, stop:1 #7c3aed);
                    border-radius: 10px;
                }
            """)
            self._title_label.setStyleSheet("font-size: 12px; border: none; color: white; font-weight: 600; background: transparent;")
            self._count_label.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.7); border: none; background: transparent;")
            self._rename_btn.set_colors("#ffffff", "#e0e7ff")
            self._delete_btn.set_colors("#ffffff", "#fecaca")
        else:
            self.setStyleSheet("")
            self._title_label.setStyleSheet("font-size: 12px; border: none; font-weight: 500; background: transparent;")
            self._count_label.setStyleSheet("font-size: 10px; color: #6b7a90; border: none; background: transparent;")
            self._rename_btn.set_colors(GRAY, BLUE)
            self._delete_btn.set_colors(GRAY, DANGER)


class RenameDialog(QDialog):
    def __init__(self, current_title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Renombrar conversacion")
        self.setMinimumWidth(380)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0d1117, stop:1 #131820);
                color: #c5cdd8;
            }
            QLabel { color: #c5cdd8; }
            QLineEdit {
                background-color: #131820;
                color: #c5cdd8;
                border: 2px solid #1e2a3a;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:1 #7c3aed);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Nuevo titulo:")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        self.title_input = QLineEdit()
        self.title_input.setText(current_title)
        layout.addWidget(self.title_input)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet("background-color: #555;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Guardar")
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        self.new_title = current_title

    def accept(self):
        self.new_title = self.title_input.text().strip()
        super().accept()


class HistorySidebar(QFrame):
    conversation_selected = pyqtSignal(str)
    conversation_deleted = pyqtSignal(str)
    conversation_renamed = pyqtSignal(str, str)
    prompt_activated = pyqtSignal(str)
    prompt_deactivated = pyqtSignal()
    prompt_edited = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("history_sidebar")
        self.setFixedWidth(220)
        self._setup_ui()
        self.refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        hist_tab = QWidget()
        hist_layout = QVBoxLayout(hist_tab)
        hist_layout.setContentsMargins(8, 8, 8, 8)
        hist_layout.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel("Historial")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        header.addWidget(title)
        header.addStretch()

        new_btn = IconButton("mdi.plus", tooltip="Nueva conversacion", size=24)
        new_btn.clicked.connect(lambda: self.conversation_deleted.emit("new"))
        header.addWidget(new_btn)
        hist_layout.addLayout(header)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        hist_layout.addWidget(self.list_widget, 1)

        self.tabs.addTab(hist_tab, "Historial")

        self.prompts = PromptsPanel()
        self.prompts.prompt_activated.connect(self.prompt_activated.emit)
        self.prompts.prompt_deactivated.connect(self.prompt_deactivated.emit)
        self.prompts.prompt_edited.connect(self.prompt_edited.emit)
        self.tabs.addTab(self.prompts, "Prompts")

        layout.addWidget(self.tabs)

    def refresh_list(self, selected_id: str = None):
        self.list_widget.clear()
        conversations = list_conversations()
        for conv in conversations:
            item_widget = HistoryItemWidget(
                conv["id"], conv["title"], conv["msg_count"]
            )
            item_widget.clicked.connect(self._on_click)
            item_widget.delete_clicked.connect(self._on_delete)
            item_widget.rename_clicked.connect(self._on_rename)

            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            list_item.setData(Qt.ItemDataRole.UserRole, conv["id"])
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)

            if conv["id"] == selected_id:
                self.list_widget.setCurrentItem(list_item)
                item_widget.set_selected(True)

    def _on_click(self, conv_id: str):
        self.conversation_selected.emit(conv_id)

    def _on_delete(self, conv_id: str):
        self.conversation_deleted.emit(conv_id)

    def _on_rename(self, conv_id: str):
        self.conversation_renamed.emit(conv_id, "")

    def highlight_conversation(self, conversation_id: str):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if item.data(Qt.ItemDataRole.UserRole) == conversation_id:
                self.list_widget.setCurrentItem(item)
                if widget:
                    widget.set_selected(True)
            else:
                if widget:
                    widget.set_selected(False)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = AIEngine()
        self.worker = None
        self.model_worker = None
        self._pending_files = []
        self._busy = False
        self._cancel_requested = False
        self._is_visible = True
        self._is_compact = False
        self._current_theme = "dark"
        self._current_conv_id = None
        self._saved_normal_geometry = None
        self._gguf_worker = None
        self._gguf_pending = []
        self._gguf_send_queued = False
        self._gguf_token = 0
        self._prefer_cloud = False

        ui_config = self.engine.config.get("ui", {})
        self._current_theme = ui_config.get("theme", "dark")

        self.setWindowTitle(self.engine.config.get("ui", {}).get("window_title", "Notas.txt - Bloc de notas"))
        self.setMinimumSize(400, 300)
        self.setWindowOpacity(1.0)

        x = ui_config.get("window_x", 100)
        y = ui_config.get("window_y", 100)
        w = ui_config.get("window_w", 800)
        h = ui_config.get("window_h", 600)
        self.setGeometry(x, y, w, h)

        self.setStyleSheet(get_theme(self._current_theme))

        self._stealth_timer = QTimer()
        self._stealth_timer.setInterval(1000)
        self._stealth_timer.timeout.connect(self._reassert_stealth)

        self._setup_ui()
        self._apply_anti_capture()
        self._register_hotkey()
        QTimer.singleShot(100, self._load_models)
        QTimer.singleShot(1200, self._maybe_preload_saved_gguf)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)

        self.history_sidebar = HistorySidebar()
        self.history_sidebar.conversation_selected.connect(self._load_conversation)
        self.history_sidebar.conversation_deleted.connect(self._on_delete_conversation)
        self.history_sidebar.conversation_renamed.connect(self._on_rename_conversation)
        self.history_sidebar.prompt_activated.connect(self._on_prompt_activated)
        self.history_sidebar.prompt_deactivated.connect(self._on_prompt_deactivated)
        self.history_sidebar.prompt_edited.connect(self._on_prompt_synced)
        self.history_sidebar.prompts.set_active(self.engine.get_active_prompt())
        self.splitter.addWidget(self.history_sidebar)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.model_selector = ModelSelector()
        self.model_selector.model_changed.connect(self._on_model_changed)
        self.model_selector.test_connection.connect(self._load_models)
        right_layout.addWidget(self.model_selector)

        self.chat = ChatWidget()
        right_layout.addWidget(self.chat, 1)

        self.input_bar = InputBar()
        self.input_bar.message_sent.connect(self._on_send_message)
        self.input_bar.file_attached.connect(self._on_file_attached)
        self.input_bar.image_attached.connect(self._on_image_attached)
        self.input_bar.stop_requested.connect(self._cancel_generation)
        right_layout.addWidget(self.input_bar)

        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([220, 580])
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        right_panel.setMinimumWidth(320)

        main_layout.addWidget(self.splitter)

        self.chat.add_message(
            "Bienvenido! Selecciona un modelo de IA y escribe tu mensaje.\n\n"
            "Atajos:\n  Ctrl+Alt+Z  Mostrar/Ocultar ventana\n"
            "  F4  Exportar conversacion (.md)\n"
            "  F5  Actualizar modelos\n  F6  Configurar API Key\n"
            "  F7  Nueva conversacion\n"
            "  F9  Alternar tema\n  F10 Modo compacto\n  Esc Detener generacion\n\n"
            "Proteccion siempre activa:\n"
            "  La ventana esta excluida de capturas/streamings mientras esta\n"
            "  visible. Pulsa Ctrl+Alt+Z para ocultarla o mostrarla.",
            is_user=False
        )

    def _apply_anti_capture(self):
        hwnd = int(self.winId())
        hide_from_processes()
        setup_stealth_window(hwnd)
        exclude_from_capture(hwnd)
        self.show()
        self._stealth_timer.start()

    def _reassert_stealth(self):
        if not self._is_visible:
            return
        try:
            hwnd = int(self.winId())
            if hwnd and not is_excluded_from_capture(hwnd):
                exclude_from_capture(hwnd)
        except Exception:
            pass
        try:
            spoof_process_visibility()
        except Exception:
            pass

    def _register_hotkey(self):
        hwnd = int(self.winId())
        register_hotkey(hwnd, HOTKEY_ID_TOGGLE)
        self._hotkey_filter = HotkeyFilter(self._toggle_visibility)
        QApplication.instance().installNativeEventFilter(self._hotkey_filter)

    def _toggle_visibility(self):
        if self._is_visible:
            self._hide_window()
        else:
            self._show_window()

    def _hide_window(self):
        hwnd = int(self.winId())
        if hwnd:
            restore_capture(hwnd)
        self.hide()
        self._is_visible = False

    def _show_window(self):
        hwnd = int(self.winId())
        if hwnd:
            setup_stealth_window(hwnd)
            exclude_from_capture(hwnd)
        self.show()
        self._is_visible = True
        self.setWindowOpacity(1.0)
        self.activateWindow()
        self.raise_()
        if hwnd:
            QTimer.singleShot(0, self._delayed_stealth_apply)

    def show_from_second_instance(self):
        """Llamado cuando el usuario abre otra instancia: muestra la ventana existente."""
        if self._is_visible:
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
            self.show()
            self.raise_()
            self.activateWindow()
        else:
            self._show_window()

    def _delayed_stealth_apply(self):
        if not self._is_visible:
            return
        try:
            hwnd = int(self.winId())
            if hwnd and not is_excluded_from_capture(hwnd):
                setup_stealth_window(hwnd)
        except Exception:
            pass

    def _set_busy(self, busy: bool):
        self._busy = busy

    def closeEvent(self, event):
        self._stealth_timer.stop()
        self.model_selector.stop_timers()
        self._auto_save_conversation()
        geom = self.geometry()
        self.engine.config["ui"]["window_x"] = geom.x()
        self.engine.config["ui"]["window_y"] = geom.y()
        self.engine.config["ui"]["window_w"] = geom.width()
        self.engine.config["ui"]["window_h"] = geom.height()
        self.engine.config["ui"]["theme"] = self._current_theme
        self.engine.save_config()
        hwnd = int(self.winId())
        unregister_hotkey(hwnd, HOTKEY_ID_TOGGLE)
        from utils.cleanup import cleanup_on_exit, clear_env_vars
        clear_env_vars()
        cleanup_on_exit()
        event.accept()

    def _toggle_compact_mode(self):
        if self._is_compact:
            self._exit_compact_mode()
        else:
            self._enter_compact_mode()

    def _enter_compact_mode(self):
        self._is_compact = True
        self._saved_normal_geometry = self.geometry()
        self.history_sidebar.setVisible(False)
        self.model_selector.setVisible(False)
        try:
            self.model_selector._close_picker()
        except Exception:
            pass
        self.chat.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        screen = QApplication.primaryScreen().geometry()
        compact_w = 380
        compact_h = 250
        x = screen.width() - compact_w - 20
        y = screen.height() - compact_h - 60
        self.setGeometry(x, y, compact_w, compact_h)
        self.setWindowOpacity(0.92)
        hwnd = int(self.winId())
        setup_stealth_window(hwnd)

    def _exit_compact_mode(self):
        self._is_compact = False
        self.history_sidebar.setVisible(True)
        self.model_selector.setVisible(True)
        self.chat.scroll_area.setStyleSheet("QScrollArea { border: none; background: #1e1e1e; }" if self._current_theme == "dark" else "QScrollArea { border: none; background: #f6f8fa; }")
        if self._saved_normal_geometry:
            self.setGeometry(self._saved_normal_geometry)
        self.setWindowOpacity(1.0)
        hwnd = int(self.winId())
        setup_stealth_window(hwnd)

    def _toggle_theme(self):
        if self._current_theme == "dark":
            self._current_theme = "light"
        else:
            self._current_theme = "dark"
        self.setStyleSheet(get_theme(self._current_theme))
        if self._is_compact:
            bg = "#1e1e1e" if self._current_theme == "dark" else "#f6f8fa"
            self.chat.scroll_area.setStyleSheet(f"QScrollArea {{ border: none; background: {bg}; }}")
        self.engine.config["ui"]["theme"] = self._current_theme
        self.engine.save_config()

    def _auto_save_conversation(self):
        msgs = self.engine.conversation_history
        if not msgs:
            return
        if self._current_conv_id:
            title = generate_title(msgs)
            save_conversation(title, msgs, self._current_conv_id)
        elif len(msgs) > 0:
            title = generate_title(msgs)
            self._current_conv_id = save_conversation(title, msgs)
            self.history_sidebar.refresh_list()

    def _on_new_conversation(self):
        if self.engine.conversation_history:
            self._auto_save_conversation()
        self._current_conv_id = None
        self.chat.clear_chat()
        self.engine.clear_history()
        self.chat.add_message("Nueva conversacion iniciada.", is_user=False)
        self.history_sidebar.refresh_list()

    def _on_prompt_activated(self, name: str):
        self.engine.set_active_prompt(name)

    def _on_prompt_deactivated(self):
        self.engine.set_active_prompt("")
        self.history_sidebar.prompts.set_active("")

    def _on_prompt_synced(self):
        name = self.history_sidebar.prompts.active_prompt_name()
        self.engine.set_active_prompt(name)

    def _on_delete_conversation(self, conv_id: str):
        if conv_id == "new":
            self._on_new_conversation()
            return
        delete_conversation(conv_id)
        if self._current_conv_id == conv_id:
            self._current_conv_id = None
            self.chat.clear_chat()
            self.engine.clear_history()
            self.chat.add_message("Conversacion eliminada.", is_user=False)
        self.history_sidebar.refresh_list(self._current_conv_id)

    def _on_rename_conversation(self, conv_id: str, dummy: str = ""):
        data = load_conversation(conv_id)
        if not data:
            return
        current_title = data.get("title", "")
        dialog = RenameDialog(current_title, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.new_title:
            data["title"] = dialog.new_title
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "history", f"{conv_id}.json"
            )
            if os.path.exists(filepath):
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            self.history_sidebar.refresh_list(self._current_conv_id)

    def _load_conversation(self, conv_id: str):
        data = load_conversation(conv_id)
        if not data:
            return
        self._auto_save_conversation()
        self._current_conv_id = conv_id
        self.chat.clear_chat()
        self.engine.conversation_history = data.get("messages", [])
        for msg in self.engine.conversation_history:
            is_user = msg.get("role") == "user"
            self.chat.add_message(msg.get("content", ""), is_user=is_user)
        self.history_sidebar.refresh_list(conv_id)

    def _load_models(self):
        self.model_selector.set_status("loading")
        self.model_worker = ModelLoadWorker(self.engine)
        self.model_worker.finished.connect(self._on_models_loaded)
        self.model_worker.error.connect(self._on_models_error)
        self.model_worker.start()

    def _on_models_loaded(self, models: dict):
        self.model_selector.clear_models()

        for m in models.get("local", []):
            self.model_selector.add_model(
                f"\U0001F4BB {m['name']}", "ollama", m["name"]
            )

        for m in models.get("cloud", []):
            self.model_selector.add_model(
                f"\u2601\uFE0F {m['name']}", "cloud", m["name"]
            )

        if models.get("local") or models.get("cloud"):
            if models.get("local") and not self._prefer_cloud:
                self.engine.set_model("ollama", models["local"][0]["name"])
                self.model_selector.set_current_model("ollama", models["local"][0]["name"])
            else:
                self.engine.set_model("cloud", models["cloud"][0]["name"])
                self.model_selector.set_current_model("cloud", models["cloud"][0]["name"])
            self._prefer_cloud = False
            self.model_selector.set_status("ready")
        else:
            self.model_selector.set_status("off")
            self.chat.add_message(
                "No se encontraron modelos.\n\n"
                "- Para modelos locales: Instala Ollama y descarga un modelo.\n"
                "- Para modelos en la nube: Configura tu API Key con F6.",
                is_user=False
            )

    def _on_models_error(self, error: str):
        self.model_selector.set_status("error")
        self.chat.add_message(f"Error al buscar modelos: {error}", is_user=False)

    def _on_model_changed(self, provider: str, model: str):
        self.engine.set_model(provider, model)
        if provider == "local_file":
            self._gguf_pending.clear()
            if self._gguf_send_queued and self._busy:
                self._abort_pending_send("[Envio cancelado: cambiaste de modelo.]")
            if self.engine.gguf_is_loaded():
                self.model_selector.show_gguf_ready(os.path.basename(model))
                self.model_selector.set_status("ready")
            else:
                self.model_selector.set_status("loading")
                self._start_gguf_load(model)
            return
        self.model_selector.set_status("loading")
        QTimer.singleShot(300, self._check_model_ready)

    def _maybe_preload_saved_gguf(self):
        if self.engine.current_provider != "local_file":
            return
        model = self.engine.current_model
        if not model or not os.path.exists(model):
            return
        if self.engine.gguf_is_loaded():
            self.model_selector.show_gguf_ready(os.path.basename(model))
            self.model_selector.set_status("ready")
            return
        self.model_selector.set_status("loading")
        self._start_gguf_load(model)

    def _start_gguf_load(self, path: str):
        self._gguf_token += 1
        token = self._gguf_token
        self.model_selector.show_gguf_loading(os.path.basename(path))
        worker = GGUFLoadWorker(self.engine, path)
        worker.finished.connect(lambda t=token, p=path: self._on_gguf_loaded(t, p))
        worker.error.connect(lambda msg, t=token: self._on_gguf_error(t, msg))
        self._gguf_worker = worker
        worker.start()

    def _on_gguf_loaded(self, token: int, path: str):
        if token != self._gguf_token:
            return
        self._gguf_worker = None
        self.model_selector.show_gguf_ready(os.path.basename(path))
        self.model_selector.set_status("ready")
        pending = self._gguf_pending[:]
        self._gguf_pending.clear()
        for cb in pending:
            try:
                cb()
            except Exception:
                pass

    def _on_gguf_error(self, token: int, msg: str):
        if token != self._gguf_token:
            return
        self._gguf_worker = None
        self._gguf_pending.clear()
        self.model_selector.show_gguf_error(msg)
        self.model_selector.set_status("error")
        if self._gguf_send_queued:
            self._abort_pending_send(f"Error al cargar el modelo: {msg}")
        else:
            self.chat.add_message(f"Error al cargar el modelo: {msg}", is_user=False)

    def _abort_pending_send(self, msg: str):
        self._gguf_send_queued = False
        self._mark_done()
        self.chat.finish_ai_message()
        self.input_bar.set_enabled(True)
        self.chat.add_message(msg, is_user=False)
        self.input_bar.input_field.setFocus()

    def _ensure_gguf_loaded(self, callback):
        if self.engine.current_provider != "local_file":
            callback()
            return
        if self.engine.gguf_is_loaded():
            callback()
            return
        self.model_selector.show_gguf_loading(os.path.basename(self.engine.current_model))
        self._gguf_send_queued = True
        self._gguf_pending.append(callback)
        if self._gguf_worker and self._gguf_worker.isRunning():
            return
        self._start_gguf_load(self.engine.current_model)

    def _check_model_ready(self):
        if self.engine.is_model_ready():
            self.model_selector.set_status("ready")
        else:
            self.model_selector.set_status("error")
            if self.engine.current_provider == "cloud" and not self.engine.cloud.api_key:
                self._show_api_key_dialog()

    def _show_api_key_dialog(self):
        dialog = ApiKeyDialog(self.engine, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._prefer_cloud = True
            self._load_models()

    def _on_send_message(self, text: str):
        if self._busy:
            return

        files_content = []
        for fpath in self._pending_files:
            content = read_file_content(fpath)
            if content:
                files_content.append(content)
        self._pending_files.clear()

        self.chat.add_message(text, is_user=True)

        self._set_busy(True)
        self._cancel_requested = False
        self.input_bar.set_enabled(False)
        self.input_bar.show_stop(True)
        self.model_selector.set_status("loading")
        self.chat.start_ai_message()

        self._ensure_gguf_loaded(lambda: self._start_ai_worker(text, files_content))

    def _start_ai_worker(self, text: str, files_content: list):
        self._gguf_send_queued = False
        self.worker = AIWorker(self.engine, text, files_content)
        self.worker.chunk_received.connect(self._on_chunk)
        self.worker.finished.connect(self._on_response_finished)
        self.worker.error.connect(self._on_response_error)
        self.worker.start()

    def _on_chunk(self, chunk: str):
        self.chat.append_to_last_ai(chunk)

    def _on_response_finished(self):
        self._mark_done()
        self.chat.finish_ai_message()
        self.input_bar.set_enabled(True)
        self.model_selector.set_status("ready")
        if self._cancel_requested:
            self.chat.add_message("[Generacion detenida]", is_user=False)
            self._cancel_requested = False
        self.input_bar.input_field.setFocus()

    def _on_response_error(self, error: str):
        self._mark_done()
        self.chat.finish_ai_message()
        self.chat.add_message(f"Error: {error}", is_user=False)
        self.input_bar.set_enabled(True)
        if self.engine.current_provider == "local_file":
            self.model_selector.show_gguf_error(error)
        else:
            self.model_selector.set_status("error")
        self.input_bar.input_field.setFocus()

    def _cancel_generation(self):
        if self.worker and self.worker.isRunning():
            self._cancel_requested = True
            self.worker.requestInterruption()
            self.worker.wait(2000)

    def _on_file_attached(self, filepath: str):
        self._pending_files.append(filepath)
        name = os.path.basename(filepath)
        self.chat.add_file_attachment(name, is_user=True)

    def _on_image_attached(self, filepath: str, pixmap):
        self._pending_files.append(filepath)
        self.chat.add_image_preview(pixmap, os.path.basename(filepath))

    def _export_conversation(self):
        from utils.export import save_conversation_markdown
        msgs = self.engine.conversation_history
        if not msgs:
            self.chat.add_message("No hay mensajes para exportar.", is_user=False)
            return
        title = "Conversacion"
        if self._current_conv_id:
            data = load_conversation(self._current_conv_id)
            if data:
                title = data.get("title", title)
        try:
            filepath = save_conversation_markdown(msgs, title)
            self.chat.add_message(f"Conversacion exportada: {os.path.basename(filepath)}", is_user=False)
        except Exception as e:
            self.chat.add_message(f"Error al exportar: {e}", is_user=False)

    def _mark_done(self):
        self._busy = False
        self._cancel_requested = False
        self.input_bar.show_stop(False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F4:
            self._export_conversation()
        elif event.key() == Qt.Key.Key_F5:
            self._load_models()
        elif event.key() == Qt.Key.Key_F6:
            self._show_api_key_dialog()
        elif event.key() == Qt.Key.Key_F7:
            self._on_new_conversation()
        elif event.key() == Qt.Key.Key_F9:
            self._toggle_theme()
        elif event.key() == Qt.Key.Key_F10:
            self._toggle_compact_mode()
        elif event.key() == Qt.Key.Key_Escape and self._busy:
            self._cancel_generation()
        elif event.key() == Qt.Key.Key_Escape and self._is_compact:
            self._exit_compact_mode()
        else:
            super().keyPressEvent(event)
