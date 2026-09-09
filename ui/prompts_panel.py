from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QDialog, QLineEdit, QPlainTextEdit,
    QMessageBox, QApplication, QStyledItemDelegate, QStyle, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from ui.icon_helpers import IconButton, DANGER, GRAY, GREEN

from utils.prompts import (
    list_prompts, read_prompt, save_prompt, delete_prompt, rename_prompt,
    new_prompt_name
)
from core.anti_capture import (
    setup_stealth_window, exclude_from_capture, set_topmost
)


class PromptEditorDialog(QDialog):
    def __init__(self, name: str = "", content: str = "", mode: str = "new", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.setMinimumSize(520, 540)
        if mode == "new":
            self.setWindowTitle("Nuevo prompt")
        else:
            self.setWindowTitle(f"Editar: {name}")
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #d4d4d4; }
            QLabel { color: #d4d4d4; }
            QLineEdit, QPlainTextEdit {
                background-color: #3c3c3c; color: #d4d4d4;
                border: 1px solid #555; border-radius: 4px;
                padding: 8px; font-size: 12px;
            }
            QLineEdit:focus, QPlainTextEdit:focus { border-color: #0078d4; }
            QPushButton {
                background-color: #555; color: #d4d4d4;
                border: none; border-radius: 4px;
                padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #666; }
            QPushButton#save_btn {
                background-color: #0078d4; color: white;
            }
            QPushButton#save_btn:hover { background-color: #1a8ae8; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        hint = QLabel(
            "El prompt se envía como instrucciones de sistema\n"
            "antes de tus mensajes, para afinar las respuestas."
        )
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)

        name_layout = QHBoxLayout()
        name_label = QLabel("Nombre:")
        name_layout.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: Generador Ejercicios Java.md")
        self.name_input.setText(name)
        name_layout.addWidget(self.name_input, 1)
        layout.addLayout(name_layout)

        content_label = QLabel("Contenido (Markdown / texto):")
        layout.addWidget(content_label)

        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.setPlaceholderText("Pega aquí tu prompt...")
        self.editor.setPlainText(content)
        layout.addWidget(self.editor, 1)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        save_btn = QPushButton("Guardar")
        save_btn.setObjectName("save_btn")
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Prompt", "Escribe un nombre para el prompt.")
            return
        super().accept()

    def showEvent(self, event):
        super().showEvent(event)
        try:
            hwnd = int(self.winId())
            setup_stealth_window(hwnd)
            exclude_from_capture(hwnd)
            set_topmost(hwnd)
        except Exception:
            pass

    def result_name(self) -> str:
        return self.name_input.text().strip()

    def result_content(self) -> str:
        return self.editor.toPlainText()


class _PromptDelegate(QStyledItemDelegate):
    """Pinta el prompt activo en verde con chulito, ignorando la seleccion."""

    def __init__(self, panel):
        super().__init__(panel.list_widget)
        self._panel = panel

    def paint(self, painter, option, index):
        name = index.data(Qt.ItemDataRole.UserRole) or ""
        active = bool(name) and name == self._panel._active_prompt
        rect = option.rect
        painter.save()
        painter.setClipRect(rect)
        if active:
            painter.fillRect(rect, QColor("#0f2e22"))
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(rect, QColor("#18212e"))
        font = option.font
        if active:
            font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#4ade80") if active else QColor("#c5cdd8"))
        text = ("\u2713  " + name) if active else name
        elided = painter.fontMetrics().elidedText(
            text, Qt.TextElideMode.ElideRight, max(0, rect.width() - 16)
        )
        painter.drawText(
            rect.adjusted(8, 0, -8, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            elided
        )
        painter.restore()


class PromptsPanel(QWidget):
    prompt_activated = pyqtSignal(str)
    prompt_deactivated = pyqtSignal()
    prompt_edited = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_prompt = ""
        self._setup_ui()
        self.refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Prompts")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        subtitle = QLabel("Instrucciones que se\nenvian a la IA con tu mensaje.")
        subtitle.setStyleSheet("font-size: 10px; color: #6b7a90;")
        layout.addWidget(subtitle)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        self.list_widget.setItemDelegate(_PromptDelegate(self))
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.currentItemChanged.connect(lambda a, b: self._update_footer())
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self.new_btn = IconButton("mdi.plus", tooltip="Nuevo prompt", size=26)
        self.new_btn.clicked.connect(self._new_prompt)
        btn_row.addWidget(self.new_btn)

        self.edit_btn = IconButton("mdi.pencil-outline", tooltip="Editar contenido", size=26)
        self.edit_btn.clicked.connect(self._edit_prompt)
        btn_row.addWidget(self.edit_btn)

        self.rename_btn = IconButton("mdi.pencil-box-outline", tooltip="Renombrar", size=26)
        self.rename_btn.clicked.connect(self._rename_prompt)
        btn_row.addWidget(self.rename_btn)

        self.copy_btn = IconButton("mdi.content-copy", tooltip="Copiar al portapapeles", size=26)
        self.copy_btn.clicked.connect(self._copy_prompt)
        btn_row.addWidget(self.copy_btn)

        self.del_btn = IconButton("mdi.trash-can-outline", tooltip="Eliminar", size=26,
                                  variant="danger", hover_color=DANGER)
        self.del_btn.clicked.connect(self._delete_prompt)
        btn_row.addWidget(self.del_btn)

        layout.addLayout(btn_row)

        self.footer = QLabel()
        self.footer.setWordWrap(True)
        self.footer.setStyleSheet("font-size: 10px; color: #4ade80;")
        layout.addWidget(self.footer)

        self.hint = QLabel("Doble clic para activar/desactivar.\nClic derecho para mas opciones.")
        self.hint.setStyleSheet("font-size: 10px; color: #6b7a90;")
        layout.addWidget(self.hint)

    def set_active(self, name: str):
        self._active_prompt = name
        self.refresh_list()

    def active_prompt_name(self) -> str:
        return self._active_prompt

    def current_prompt_name(self) -> str:
        item = self.list_widget.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return ""

    def refresh_list(self):
        prev = self.current_prompt_name()
        self.list_widget.clear()
        for name in list_prompts():
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_widget.addItem(item)

        if self.list_widget.count() == 0:
            empty = QListWidgetItem("Sin prompts todavia.\nPulsa + para crear uno.")
            empty.setFlags(empty.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            empty.setForeground(Qt.GlobalColor.gray)
            self.list_widget.addItem(empty)

        restore = ""
        if prev and prev != self._active_prompt:
            restore = prev
        elif self._active_prompt:
            restore = self._active_prompt
        if restore:
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) == restore:
                    self.list_widget.setCurrentRow(i)
                    break

        self._update_footer()

    def _get_name(self) -> str:
        return self.current_prompt_name()

    def _new_prompt(self):
        dialog = PromptEditorDialog(name=new_prompt_name(), mode="new", parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            save_prompt(dialog.result_name(), dialog.result_content())
            self.refresh_list()
            self.prompt_edited.emit()

    def _edit_prompt(self):
        name = self._get_name()
        if not name:
            return
        content = read_prompt(name)
        dialog = PromptEditorDialog(name=name, content=content, mode="edit", parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.result_name()
            if new_name != name and not rename_prompt(name, new_name):
                QMessageBox.warning(
                    self, "Prompt",
                    "No se pudo renombrar: ya existe un prompt con ese nombre."
                )
                return
            saved_name = new_name if new_name else name
            if self._active_prompt == name:
                self._active_prompt = saved_name
            save_prompt(saved_name, dialog.result_content())
            self.refresh_list()
            self.prompt_edited.emit()

    def _rename_prompt(self):
        name = self._get_name()
        if not name:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Renombrar prompt")
        dialog.setMinimumWidth(360)
        dialog.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #d4d4d4; }
            QLabel { color: #d4d4d4; }
            QLineEdit {
                background-color: #3c3c3c; color: #d4d4d4;
                border: 1px solid #555; border-radius: 4px; padding: 8px;
            }
            QPushButton {
                background-color: #555; color: #d4d4d4;
                border: none; border-radius: 4px; padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #666; }
            QPushButton#save_btn { background-color: #0078d4; color: white; }
        """)
        lay = QVBoxLayout(dialog)
        lay.addWidget(QLabel("Nuevo nombre:"))
        name_input = QLineEdit(name)
        lay.addWidget(name_input)
        btn_row = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel)
        btn_row.addStretch()
        save = QPushButton("Renombrar")
        save.setObjectName("save_btn")
        save.clicked.connect(dialog.accept)
        btn_row.addWidget(save)
        lay.addLayout(btn_row)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_name = name_input.text().strip()
        if new_name == name or not new_name:
            return
        if not rename_prompt(name, new_name):
            QMessageBox.warning(
                self, "Prompt",
                "No se pudo renombrar: ya existe un prompt con ese nombre."
            )
            return
        if self._active_prompt == name:
            self._active_prompt = new_name
        self.refresh_list()
        self.prompt_edited.emit()

    def _copy_prompt(self):
        name = self._get_name()
        if not name:
            return
        content = read_prompt(name)
        QApplication.clipboard().setText(content)
        self.copy_btn.flash_icon("mdi.check", GREEN)
        QApplication.processEvents()
        QTimer.singleShot(1200, lambda: self.copy_btn.flash_icon("mdi.content-copy", GRAY))

    def _delete_prompt(self):
        name = self._get_name()
        if not name:
            return
        answer = QMessageBox.question(
            self, "Eliminar prompt",
            f"¿Eliminar \"{name}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if answer == QMessageBox.StandardButton.Yes:
            delete_prompt(name)
            if name == self._active_prompt:
                self.set_active("")
            else:
                self.refresh_list()
            self.prompt_edited.emit()

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        name = item.data(Qt.ItemDataRole.UserRole) or ""
        if not name:
            return
        self.list_widget.setCurrentItem(item)
        menu = QMenu(self)
        if name == self._active_prompt:
            act_toggle = menu.addAction("\u2713 Desactivar prompt")
        else:
            act_toggle = menu.addAction("\u2713 Activar prompt")
        menu.addSeparator()
        act_rename = menu.addAction("\u270E Renombrar")
        act_edit = menu.addAction("\u270E Editar contenido")
        act_copy = menu.addAction("\u29C9 Copiar al portapapeles")
        menu.addSeparator()
        act_del = menu.addAction("\U0001F5D1 Eliminar")
        chosen = menu.exec(self.list_widget.viewport().mapToGlobal(pos))
        if chosen == act_toggle:
            self._on_item_double_clicked(item)
        elif chosen == act_rename:
            self._rename_prompt()
        elif chosen == act_edit:
            self._edit_prompt()
        elif chosen == act_copy:
            self._copy_prompt()
        elif chosen == act_del:
            self._delete_prompt()

    def _update_footer(self):
        name = self._get_name()
        if not name:
            if self._active_prompt:
                self.footer.setText(f"Activo: {self._active_prompt}")
            else:
                self.footer.setText("Selecciona un prompt para ver sus datos.")
            return
        content = read_prompt(name)
        chars = len(content)
        words = len(content.split())
        estado = "Activo" if name == self._active_prompt else "Inactivo"
        self.footer.setText(
            f"{name}  \u00b7  {chars} caracteres  \u00b7  {words} palabras  \u00b7  {estado}"
        )

    def _on_item_double_clicked(self, item):
        name = item.data(Qt.ItemDataRole.UserRole) or ""
        if not name:
            return
        if name == self._active_prompt:
            self.set_active("")
            self.prompt_deactivated.emit()
        else:
            self.set_active(name)
            self.prompt_activated.emit(name)