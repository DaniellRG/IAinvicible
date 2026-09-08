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
    def __init__(self, current_key: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar API Key")
        self.setMinimumWidth(420)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #d4d4d4; }
            QLabel { color: #d4d4d4; }
            QLineEdit {
                background-color: #3c3c3c; color: #d4d4d4;
                border: 1px solid #555; border-radius: 4px;
                padding: 8px; font-size: 12px;
            }
            QPushButton {
                background-color: #0078d4; color: white;
                border: none; border-radius: 4px;
                padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1a8ae8; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Ingresa tu API Key de OpenAI:")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("sk-...")
        self.key_input.setText(current_key)
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.key_input)

        self.toggle_btn = QPushButton("Mostrar")
        self.toggle_btn.setFixedWidth(100)
        self.toggle_btn.clicked.connect(self._toggle_visibility)
        layout.addWidget(self.toggle_btn)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet("background-color: #555;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Guardar")
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        self.api_key = current_key

    def _toggle_visibility(self):
        if self.key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setText("Ocultar")
        else:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setText("Mostrar")

    def accept(self):
        self.api_key = self.key_input.text().strip()
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

        self._rename_btn = QPushButton("\u270E")
        self._rename_btn.setObjectName("history_delete_btn")
        self._rename_btn.setFixedSize(24, 24)
        self._rename_btn.setToolTip("Renombrar")
        self._rename_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rename_btn.clicked.connect(lambda: self.rename_clicked.emit(self._conv_id))
        layout.addWidget(self._rename_btn)

        self._delete_btn = QPushButton("\U0001F5D1")
        self._delete_btn.setObjectName("history_delete_btn")
        self._delete_btn.setFixedSize(24, 24)
        self._delete_btn.setToolTip("Eliminar")
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
            self._rename_btn.setStyleSheet("color: white; background: transparent; border: none; font-size: 12px;")
            self._delete_btn.setStyleSheet("color: white; background: transparent; border: none; font-size: 12px;")
        else:
            self.setStyleSheet("")
            self._title_label.setStyleSheet("font-size: 12px; border: none; font-weight: 500; background: transparent;")
            self._count_label.setStyleSheet("font-size: 10px; color: #6b7a90; border: none; background: transparent;")
            self._rename_btn.setObjectName("history_delete_btn")
            self._delete_btn.setObjectName("history_delete_btn")


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

        new_btn = QPushButton("+")
        new_btn.setObjectName("history_delete_btn")
        new_btn.setFixedSize(24, 24)
        new_btn.setToolTip("Nueva conversacion")
        new_btn.clicked.connect(lambda: self.conversation_deleted.emit("new"))
        header.addWidget(new_btn)
        hist_layout.addLayout(header)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        hist_layout.addWidget(self.list_widget, 1)

        self.tabs.addTab(hist_tab, "Historial")

        self.prompts = PromptsPanel()
        self.prompts.prompt_activated.connect(self.prompt_activated.emit)
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
        self._auto_hide_enabled = False
        self._auto_hide_seconds = 15
        self._is_hidden_by_auto = False
        self._is_compact = False
        self._current_theme = "dark"
        self._current_conv_id = None
        self._saved_normal_geometry = None
        self._gguf_worker = None
        self._gguf_pending = []
        self._gguf_send_queued = False
        self._gguf_token = 0

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

        self._auto_hide_timer = QTimer()
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self._auto_hide)

        self._stealth_timer = QTimer()
        self._stealth_timer.setInterval(1000)
        self._stealth_timer.timeout.connect(self._reassert_stealth)

        self._setup_ui()
        self._apply_anti_capture()
        self._register_hotkey()
        self._start_auto_hide_timer()
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

        main_layout.addWidget(self.splitter)

        self.chat.add_message(
            "Bienvenido! Selecciona un modelo de IA y escribe tu mensaje.\n\n"
            "Atajos:\n  Ctrl+Alt+Z  Mostrar/Ocultar ventana\n"
            "  F4  Exportar conversacion (.md)\n"
            "  F5  Actualizar modelos\n  F6  Configurar API Key\n"
            "  F7  Nueva conversacion\n  F8  Auto-hide 15s on/off (off)\n"
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
        if not self._is_visible or self._is_hidden_by_auto:
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
        self._auto_hide_timer.stop()

    def _show_window(self):
        hwnd = int(self.winId())
        if hwnd:
            setup_stealth_window(hwnd)
            exclude_from_capture(hwnd)
        self.show()
        self._is_visible = True
        self.setWindowOpacity(1.0)
        self._is_hidden_by_auto = False
        self.activateWindow()
        self.raise_()
        self._start_auto_hide_timer()
        if hwnd:
            QTimer.singleShot(0, self._delayed_stealth_apply)

    def _delayed_stealth_apply(self):
        if not self._is_visible:
            return
        try:
            hwnd = int(self.winId())
            if hwnd and not is_excluded_from_capture(hwnd):
                setup_stealth_window(hwnd)
        except Exception:
            pass

    def _start_auto_hide_timer(self):
        if self._auto_hide_enabled:
            self._auto_hide_timer.start(self._auto_hide_seconds * 1000)

    def _auto_hide(self):
        if self._is_visible and self._auto_hide_enabled and not self._busy:
            hwnd = int(self.winId())
            if hwnd:
                restore_capture(hwnd)
            self.hide()
            self._is_visible = False
            self._is_hidden_by_auto = True
            self._auto_hide_timer.stop()

    def _set_busy(self, busy: bool):
        self._busy = busy

    def _reset_auto_hide(self):
        if self._is_hidden_by_auto:
            self._show_window()
        else:
            self._start_auto_hide_timer()

    def mouseMoveEvent(self, event):
        self._reset_auto_hide()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        self._reset_auto_hide()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._reset_auto_hide()
        super().enterEvent(event)

    def focusInEvent(self, event):
        self._reset_auto_hide()
        super().focusInEvent(event)

    def closeEvent(self, event):
        self._auto_hide_timer.stop()
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
        self.chat.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        screen = QApplication.primaryScreen().geometry()
        compact_w = 380
        compact_h = 200
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
        if self.engine.set_active_prompt(name):
            self.chat.add_message(f"Prompt activado: {name}", is_user=False)
        else:
            self.history_sidebar.prompts.refresh_list()
            self.chat.add_message("No se pudo activar el prompt.", is_user=False)

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
            if models.get("local"):
                self.engine.set_model("ollama", models["local"][0]["name"])
                self.model_selector.set_current_model("ollama", models["local"][0]["name"])
            elif models.get("cloud"):
                self.engine.set_model("cloud", models["cloud"][0]["name"])
                self.model_selector.set_current_model("cloud", models["cloud"][0]["name"])
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
        current_key = self.engine.config.get("cloud", {}).get("api_key", "")
        dialog = ApiKeyDialog(current_key, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.engine.set_api_key(dialog.api_key)
            QTimer.singleShot(200, self._check_model_ready)

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
        self._auto_hide_timer.stop()

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
        self._start_auto_hide_timer()

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
        self._reset_auto_hide()
        if event.key() == Qt.Key.Key_F4:
            self._export_conversation()
        elif event.key() == Qt.Key.Key_F5:
            self._load_models()
        elif event.key() == Qt.Key.Key_F6:
            self._show_api_key_dialog()
        elif event.key() == Qt.Key.Key_F7:
            self._on_new_conversation()
        elif event.key() == Qt.Key.Key_F8:
            self._auto_hide_enabled = not self._auto_hide_enabled
            if self._auto_hide_enabled:
                self.chat.add_message("Auto-hide: ACTIVADO (se oculta en 15s)", is_user=False)
                self._start_auto_hide_timer()
            else:
                self.chat.add_message("Auto-hide: DESACTIVADO", is_user=False)
                self._auto_hide_timer.stop()
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
