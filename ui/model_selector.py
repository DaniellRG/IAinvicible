import os
import subprocess
import ctypes
import itertools
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QLabel,
    QPushButton, QFrame, QVBoxLayout, QListWidget,
    QListWidgetItem, QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread

from ui.icon_helpers import IconButton


OLLAMA_PATHS = [
    os.path.expanduser("~\\.ollama\\models\\blobs"),
    "C:\\Users\\{}\\.ollama\\models\\blobs".format(os.getenv("USERNAME", "")),
]

OLLAMA_MANIFESTS = os.path.expanduser("~\\.ollama\\models\\manifests\\registry.ollama.ai\\library")

# Carpetas que se omiten al buscar en toda la PC (para no tardar horas)
PC_SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", ".cache", "AppData",
    "$RECYCLE.BIN", "System Volume Information", "python_embed",
    "Intel", "AMD", "NVIDIA", "Windows", "Program Files",
    "Program Files (x86)", ".ollama", "history", "build", "dist",
    "ProgramData", "Recovery", ".venv", "venv", ".gradle", ".m2", ".npm",
}

# Al escanear un disco/USB concreto solo se omiten las carpetas de sistema
# (así los modelos en una USB se encuentran sin importar donde estén).
DRIVE_SKIP_DIRS = {
    "$RECYCLE.BIN", "System Volume Information", "Windows",
    "Program Files", "Program Files (x86)", "node_modules",
    ".git", "__pycache__",
}

MODEL_EXTENSIONS = (".gguf", ".bin", ".pt", ".safetensors", ".pth", ".onnx", ".ckpt")

DRIVE_TYPES = {2: "USB / Removible", 3: "Local", 4: "Red", 5: "CD/DVD", 6: "RAM"}


def _volume_label(root: str) -> str:
    try:
        buf = ctypes.create_unicode_buffer(261)
        if ctypes.windll.kernel32.GetVolumeInformationW(root, buf, 261, None, None, None, None, 0):
            return buf.value
    except Exception:
        pass
    return ""


def _free_gb(root: str) -> float:
    try:
        free = ctypes.c_ulonglong()
        if ctypes.windll.kernel32.GetDiskFreeSpaceExW(root, ctypes.byref(free), None, None):
            return free.value / (1024 ** 3)
    except Exception:
        pass
    return 0.0


def list_drives() -> list:
    """Devuelve (root, tipo, etiqueta, gb_libres) de cada unidad/USB detectado."""
    drives = []
    try:
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i in range(26):
            if bitmask & (1 << i):
                root = chr(ord("A") + i) + ":\\"
                dtype = ctypes.windll.kernel32.GetDriveTypeW(root)
                drives.append((root, dtype, _volume_label(root), _free_gb(root)))
    except Exception:
        drives = [
            (chr(ord("A") + i) + ":\\", 0, "", 0.0)
            for i in range(26)
            if os.path.exists(chr(ord("A") + i) + ":\\")
        ]
    return drives


def get_fixed_drive_roots() -> list:
    roots = [root for root, t, _, _ in list_drives() if t == 3]
    return roots or ["C:\\"]


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
    """Escaneo en paralelo de una o mas raices.

    Emite:
      - batch: lista de hallazgos acumulados (para mostrarlos en vivo)
      - progress: texto con la ubicacion que se esta analizando
      - finished: lista completa ordenada
    Cada hallazgo es ("file", nombre, ruta, size_mb) o ("ollama", nombre) para
    modelos de Ollama encontrados dentro de un .ollama.
    """

    batch = pyqtSignal(list)
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)

    def __init__(self, folders, pc: bool = False):
        super().__init__()
        self.folders = [folders] if isinstance(folders, str) else list(folders)
        self.pc = pc
        self._cancel = False
        self._seen_ollama = set()
        self._counter = itertools.count()

    def stop(self):
        self._cancel = True

    def _check_ollama(self, ollama_dir, found):
        manifest_base = os.path.join(
            ollama_dir, "models", "manifests", "registry.ollama.ai", "library"
        )
        if not os.path.isdir(manifest_base):
            return
        try:
            for model_dir in os.listdir(manifest_base):
                model_path = os.path.join(manifest_base, model_dir)
                if os.path.isdir(model_path):
                    for tag in os.listdir(model_path):
                        full = f"{model_dir}:{tag}" if tag != "latest" else model_dir
                        if full not in self._seen_ollama:
                            self._seen_ollama.add(full)
                            found.append(("ollama", full))
        except Exception:
            pass

    def _walk(self, root):
        walk_found = []
        skip = PC_SKIP_DIRS if self.pc else DRIVE_SKIP_DIRS
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                if self._cancel:
                    return walk_found
                pruned = []
                for d in dirnames:
                    if d in skip:
                        continue
                    if d == ".ollama":
                        self._check_ollama(os.path.join(dirpath, d), walk_found)
                        continue
                    pruned.append(d)
                dirnames[:] = pruned

                n = next(self._counter)
                if n % 150 == 0:
                    self.progress.emit(dirpath)

                for f in filenames:
                    if f.lower().endswith(MODEL_EXTENSIONS):
                        full = os.path.join(dirpath, f)
                        try:
                            size_mb = os.path.getsize(full) / (1024 * 1024)
                        except Exception:
                            size_mb = 0
                        walk_found.append(("file", f, full, size_mb))
        except Exception:
            pass
        return walk_found

    def run(self):
        tasks = []
        for folder in self.folders:
            try:
                entries = os.listdir(folder)
                if not entries:
                    continue
                for entry in entries:
                    full = os.path.join(folder, entry)
                    if os.path.isdir(full):
                        tasks.append(full)
            except Exception:
                tasks.append(folder)

        found = []
        workers = max(1, min(4, len(tasks)))
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(self._walk, t) for t in tasks]
                for fut in as_completed(futures):
                    if self._cancel:
                        break
                    chunk = fut.result()
                    if chunk:
                        self.batch.emit(chunk)
                        found.extend(chunk)
        except Exception:
            pass

        if self._cancel:
            return

        found.sort(key=lambda x: (x[0], x[1].lower()))
        self.finished.emit(found)


class ModelSelector(QWidget):
    model_changed = pyqtSignal(str, str)
    test_connection = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("header_bar")
        self._loading = False
        self._all_models = []
        self._scanning = False
        self._scan_token = 0
        self._folder_worker = None
        self._selected_drive = ""
        self._found_items = []
        self._seen = set()
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
        layout.setSpacing(8)

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

        self.ollama_btn = QPushButton("\U0001F999")
        self.ollama_btn.setObjectName("attach_btn")
        self.ollama_btn.setFixedSize(32, 32)
        self.ollama_btn.setToolTip("Ollama local")
        self.ollama_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ollama_btn.clicked.connect(self._toggle_ollama)
        layout.addWidget(self.ollama_btn)

        self.folder_btn = QPushButton("\U0001F4C2")
        self.folder_btn.setObjectName("attach_btn")
        self.folder_btn.setFixedSize(32, 32)
        self.folder_btn.setToolTip("Examinar carpeta")
        self.folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.folder_btn.clicked.connect(self._toggle_folder)
        layout.addWidget(self.folder_btn)

        self.search_btn = QPushButton("\U0001F50D")
        self.search_btn.setObjectName("attach_btn")
        self.search_btn.setFixedSize(32, 32)
        self.search_btn.setToolTip("Buscar modelos (PC / Discos)")
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.clicked.connect(self._toggle_search_menu)
        layout.addWidget(self.search_btn)

        self.refresh_btn = QPushButton("\u21bb")
        self.refresh_btn.setObjectName("attach_btn")
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.setToolTip("Actualizar modelos de Ollama")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.test_connection.emit)
        layout.addWidget(self.refresh_btn)

        outer.addLayout(layout)

        outer.addWidget(self._build_picker_panel())

        self.set_status("off")

    def _build_picker_panel(self):
        self._picker_mode = ""
        self.picker_panel = QFrame()
        self.picker_panel.setObjectName("picker_panel")
        self.picker_panel.setStyleSheet("""
            QFrame#picker_panel {
                background-color: #252526;
                border: 1px solid #333;
                border-radius: 8px;
                margin: 0 14px 8px 14px;
            }
            QLabel { color: #d4d4d4; background: transparent; border: none; }
            QLabel#picker_icon { font-size: 18px; }
            QLabel#picker_title { font-size: 13px; font-weight: bold; }
            QLabel#picker_info { color: #888; font-size: 11px; }
            QListWidget {
                background-color: #1e1e1e; color: #d4d4d4;
                border: 1px solid #444; border-radius: 6px;
                font-size: 12px;
            }
            QListWidget::item { padding: 6px 8px; }
            QListWidget::item:selected { background-color: #094771; }
            QListWidget::item:hover { background-color: #2d2d2d; }
        """)
        self.picker_panel.setVisible(False)

        panel_layout = QVBoxLayout(self.picker_panel)
        panel_layout.setContentsMargins(10, 8, 10, 10)
        panel_layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        self.picker_icon = QLabel()
        self.picker_icon.setObjectName("picker_icon")
        header_row.addWidget(self.picker_icon)

        self.picker_title = QLabel()
        self.picker_title.setObjectName("picker_title")
        header_row.addWidget(self.picker_title)

        header_row.addStretch()

        close_btn = IconButton("mdi.close", tooltip="Cerrar", size=24)
        close_btn.clicked.connect(self._close_picker)
        header_row.addWidget(close_btn)

        panel_layout.addLayout(header_row)

        self.picker_info = QLabel()
        self.picker_info.setObjectName("picker_info")
        panel_layout.addWidget(self.picker_info)

        self.picker_list = QListWidget()
        self.picker_list.setMaximumHeight(220)
        self.picker_list.itemClicked.connect(self._on_picker_item_clicked)
        panel_layout.addWidget(self.picker_list)

        self.scan_btn = QPushButton("Escanear")
        self.scan_btn.setObjectName("scan_btn")
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.setEnabled(False)
        self.scan_btn.setVisible(False)
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6; color: white;
                border: none; border-radius: 6px;
                padding: 7px 18px; font-weight: 600;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #2d3a4a; color: #6b7a90; }
        """)
        self.scan_btn.clicked.connect(self._on_scan_btn_clicked)
        panel_layout.addWidget(self.scan_btn, 0, Qt.AlignmentFlag.AlignRight)

        self._picker_anim = None
        return self.picker_panel

    # ------------------------------------------------------------------
    #  Botones: Ollama local / Examinar carpeta / Buscar en PC
    # ------------------------------------------------------------------

    def _toggle_panel(self, mode: str, icon: str, title: str, info: str):
        if self._picker_mode == mode and self.picker_panel.isVisible():
            self._close_picker()
            return
        self._picker_mode = mode
        self.picker_icon.setText(icon)
        self.picker_title.setText(title)
        self.picker_info.setText(info)
        self.picker_panel.setVisible(True)
        self.picker_list.clear()
        self._set_picker_busy_text("Buscando...")
        self._close_picker_effect()

    def _close_picker_effect(self):
        """Evita artefactos de QGraphicsOpacityEffect que pueden dejar el panel invisible."""
        if self._picker_anim is not None:
            self._picker_anim.stop()
            self._picker_anim = None
        self.picker_panel.setGraphicsEffect(None)

    def _close_picker(self):
        self._close_picker_effect()
        self.picker_panel.setVisible(False)
        self._picker_mode = ""

    def _set_picker_busy_text(self, text: str):
        self.picker_list.clear()
        item = QListWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        item.setForeground(Qt.GlobalColor.gray)
        self.picker_list.addItem(item)

    def _toggle_ollama(self):
        self._toggle_panel("ollama", "\U0001F999", "Ollama local", "Modelos detectados en Ollama:")
        self._scan_ollama()

    def _toggle_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta con modelos")
        if not folder:
            return
        self._toggle_panel("folder", "\U0001F4C2", "Examinar carpeta", f"Carpeta: {folder}")
        self._scan_folder(folder, pc=False)

    def _toggle_search_menu(self):
        self._cancel_current_scan()
        if self._picker_mode == "searchmenu" and self.picker_panel.isVisible():
            self._close_picker()
            return
        self._picker_mode = "searchmenu"
        self.picker_icon.setText("\U0001F50D")
        self.picker_title.setText("Buscar modelos")
        self.picker_info.setText("Elige como quieres buscar:")
        self.scan_btn.setVisible(False)
        self.picker_list.clear()

        menu = [
            ("\U0001F4BB  Toda la PC", "pc"),
            ("\U0001F4BD  Discos y USB", "drives"),
        ]
        for text, opt_id in menu:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, ["menu_opt", opt_id])
            self.picker_list.addItem(item)
        self.picker_panel.setVisible(True)
        self._close_picker_effect()

    def _on_search_menu_option(self, opt_id: str):
        self._cancel_current_scan()
        if opt_id == "pc":
            self._picker_mode = "pc"
            self.picker_title.setText("\U0001F4BB Toda la PC")
            self.picker_info.setText("Buscando modelos en todo el equipo...")
            self._scan_folder(get_fixed_drive_roots(), pc=True)
        elif opt_id == "drives":
            self._picker_mode = "drives"
            self.picker_title.setText("\U0001F4BD Discos y USB")
            self.picker_info.setText("Elige un disco/USB y pulsa Escanear:")
            self._populate_drives()
            self.scan_btn.setEnabled(False)
            self.scan_btn.setText("Escanear")
            self.scan_btn.setVisible(True)

    def _populate_drives(self):
        self.picker_list.clear()
        for root, dtype, label, free in list_drives():
            type_name = DRIVE_TYPES.get(dtype, "Disco")
            icon = "\U0001F50C" if dtype == 2 else "\U0001F4BD"
            text = f"{icon} {root}"
            if label:
                text += f"  [{label}]"
            text += f"  ({type_name}"
            if free:
                text += f", {free:.0f} GB libres"
            text += ")"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, ["drive", root])
            self.picker_list.addItem(item)

    def _on_scan_btn_clicked(self):
        if self._scanning:
            self._cancel_current_scan()
            self.picker_info.setText("Escaneo detenido. Se muestran los hallazgos parciales.")
            return
        drive = getattr(self, "_selected_drive", "")
        if not drive:
            return
        self._picker_mode = "drive_scan"
        self.picker_title.setText(f"\U0001F50D Escaneando {drive}")
        self.picker_info.setText("Buscando modelos...")
        self._scan_folder(drive, pc=False)

    def _cancel_current_scan(self):
        self._scan_token += 1
        if self._folder_worker is not None and self._folder_worker.isRunning():
            self._folder_worker.stop()
        self._scanning = False
        self.scan_btn.setEnabled(False)

    def _set_scanning_state(self, on: bool):
        self._scanning = on
        if on:
            self.scan_btn.setText("Detener")
            self.scan_btn.setEnabled(True)
            self.scan_btn.setVisible(True)
        else:
            self.scan_btn.setText("Escanear")
            self.scan_btn.setVisible(False)

    def _scan_ollama(self):
        self._set_picker_busy_text("Escaneando modelos de Ollama...")
        self.picker_info.setText("Modelos detectados en Ollama:")
        self._ollama_worker = OllamaScanWorker()
        self._ollama_worker.finished.connect(self._on_ollama_scanned)
        self._ollama_worker.start()

    def _scan_folder(self, folders, pc: bool):
        self._scan_token += 1
        token = self._scan_token
        self._found_items = []
        self._seen = set()
        self.picker_list.clear()
        self._set_scanning_state(True)

        w = FolderScanWorker(folders, pc)
        self._folder_worker = w

        def on_batch(items):
            if token != self._scan_token:
                return
            for entry in items:
                key = entry[2] if len(entry) > 2 else entry[1]
                if key in self._seen:
                    continue
                self._seen.add(key)
                self._found_items.append(entry)
                self._add_scan_item(entry)
            self.picker_info.setText(
                f"Analizando...  {len(self._found_items)} modelos encontrados"
            )

        def on_progress(dirpath, tok=token):
            if tok != self._scan_token:
                return
            head = dirpath
            if len(head) > 40:
                head = "\u2026" + head[-39:]
            self.picker_info.setText(
                f"{len(self._found_items)} encontrados \u00b7 analizando {head}"
            )

        def on_finished(results, tok=token):
            if tok != self._scan_token:
                return
            self._render_scan_results(results)
            self._set_scanning_state(False)

        w.batch.connect(on_batch)
        w.progress.connect(on_progress)
        w.finished.connect(on_finished)
        w.start()

    def _add_scan_item(self, entry):
        if entry[0] == "ollama":
            label = f"\U0001F4BB {entry[1]}"
            data = ["ollama", entry[1]]
        else:
            name, path, size = entry[1], entry[2], entry[3]
            label = f"\U0001F4C4 {name}  ({size:.0f} MB)"
            data = ["local_file", path]
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, data)
        self.picker_list.addItem(item)

    def _render_scan_results(self, items: list):
        self.picker_list.clear()
        for entry in items:
            self._add_scan_item(entry)
        if not items:
            item = QListWidgetItem("No se encontraron archivos de modelo en esta ubicación")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item.setForeground(Qt.GlobalColor.gray)
            self.picker_list.addItem(item)

    def _on_ollama_scanned(self, models: list):
        self.picker_list.clear()
        for model in models:
            item = QListWidgetItem(f"\U0001F4BB {model}")
            item.setData(Qt.ItemDataRole.UserRole, ["ollama", model])
            self.picker_list.addItem(item)

        if not models:
            item = QListWidgetItem("No se encontraron modelos de Ollama.")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item.setForeground(Qt.GlobalColor.gray)
            self.picker_list.addItem(item)

    def _on_picker_item_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind = data[0]
        if kind == "menu_opt":
            self._on_search_menu_option(data[1])
            return
        if kind == "drive":
            self._selected_drive = data[1]
            self.scan_btn.setEnabled(True)
            return
        provider, model_id = data
        self._select_model(provider, model_id)

    def _select_model(self, provider: str, model_id: str):
        display = f"\U0001F4C2 {os.path.basename(model_id)}" if provider == "local_file" else f"\U0001F4BB {model_id}"
        existing = self.model_combo.findData((provider, model_id))
        if existing < 0:
            self._all_models.append((display, provider, model_id))
            self.model_combo.addItem(display, (provider, model_id))
            self.model_combo.setCurrentIndex(self.model_combo.count() - 1)
        else:
            self.model_combo.setCurrentIndex(existing)
        self.model_changed.emit(provider, model_id)
        self._close_picker()

    # ------------------------------------------------------------------
    #  Combo y estados
    # ------------------------------------------------------------------

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