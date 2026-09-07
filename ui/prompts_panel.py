from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QDialog, QLineEdit, QPlainTextEdit,
    QMessageBox, QApplication, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ui.animated_highlight import AnimatedHighlight
from utils.prompts import (
    list_prompts, read_prompt, save_prompt, delete_prompt, new_prompt_name
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
        if mode == "edit":
            self.name_input.setEnabled(False)
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

    def result_name(self) -> str:
        return self.name_input.text().strip()

    def result_content(self) -> str:
        return self.editor.toPlainText()


class PromptItemWidget(QWidget):
    clicked = pyqtSignal(str)
    activated = pyqtSignal(str)

    def __init__(self, name: str, is_active: bool = False, parent=None):
        super().__init__(parent)
        self._name = name
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._highlight = AnimatedHighlight(self)
        self._highlight.resize(self.width(), self.height())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 8, 6)
        layout.setSpacing(6)

        icon = QLabel("\U0001F4DD")
        icon.setStyleSheet("font-size: 13px; border: none; background: transparent;")
        icon.setFixedWidth(22)
        layout.addWidget(icon)

        self._name_label = QLabel(name)
        self._name_label.setStyleSheet("font-size: 12px; border: none; background: transparent;")
        self._name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._name_label, 1)

        self._active_label = QLabel("\u25CF Activo")
        self._active_label.setStyleSheet(
            "font-size: 10px; color: #10b981; border: none; background: transparent; font-weight: 600;"
        )
        self._active_label.setVisible(is_active)
        layout.addWidget(self._active_label)

    def set_selected(self, selected: bool, animate: bool = True):
        self._highlight.set_selected(selected, animate)
        if selected:
            self._name_label.setStyleSheet(
                "font-size: 12px; border: none; background: transparent; color: white; font-weight: 600;"
            )
        else:
            self._name_label.setStyleSheet(
                "font-size: 12px; border: none; background: transparent;"
            )

    def set_active(self, is_active: bool):
        self._active_label.setVisible(is_active)

    def mousePressEvent(self, event):
        self.clicked.emit(self._name)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.activated.emit(self._name)
        event.accept()

    def resizeEvent(self, event):
        self._highlight.resize(self.width(), self.height())
        super().resizeEvent(event)


class PromptsPanel(QWidget):
    prompt_activated = pyqtSignal(str)
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
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self.new_btn = QPushButton("+")
        self.new_btn.setObjectName("history_delete_btn")
        self.new_btn.setFixedSize(26, 26)
        self.new_btn.setToolTip("Nuevo prompt")
        self.new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_btn.clicked.connect(self._new_prompt)
        btn_row.addWidget(self.new_btn)

        self.edit_btn = QPushButton("\u270E")
        self.edit_btn.setObjectName("history_delete_btn")
        self.edit_btn.setFixedSize(26, 26)
        self.edit_btn.setToolTip("Editar")
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.clicked.connect(self._edit_prompt)
        btn_row.addWidget(self.edit_btn)

        self.copy_btn = QPushButton("\u29C9")
        self.copy_btn.setObjectName("history_delete_btn")
        self.copy_btn.setFixedSize(26, 26)
        self.copy_btn.setToolTip("Copiar al portapapeles")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_prompt)
        btn_row.addWidget(self.copy_btn)

        self.use_btn = QPushButton("\u25B6 Usar")
        self.use_btn.setObjectName("history_delete_btn")
        self.use_btn.setFixedHeight(26)
        self.use_btn.setToolTip("Activar este prompt en el chat")
        self.use_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.use_btn.clicked.connect(self._use_current)
        btn_row.addWidget(self.use_btn)

        self.del_btn = QPushButton("\U0001F5D1")
        self.del_btn.setObjectName("history_delete_btn")
        self.del_btn.setFixedSize(26, 26)
        self.del_btn.setToolTip("Eliminar")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.clicked.connect(self._delete_prompt)
        btn_row.addWidget(self.del_btn)

        layout.addLayout(btn_row)

        self.hint = QLabel("Doble clic en un prompt para activarlo.")
        self.hint.setStyleSheet("font-size: 10px; color: #6b7a90;")
        layout.addWidget(self.hint)

    def set_active(self, name: str):
        self._active_prompt = name
        self.refresh_list()

    def current_prompt_name(self) -> str:
        item = self.list_widget.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return ""

    def refresh_list(self):
        self.list_widget.clear()
        for name in list_prompts():
            widget = PromptItemWidget(name, is_active=(name == self._active_prompt))
            widget.clicked.connect(self._on_item_clicked)
            widget.activated.connect(self._activate)
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setToolTip("Doble clic para activar")
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

        if self.list_widget.count() == 0:
            empty = QListWidgetItem("Sin prompts todavia.\nPulsa + para crear uno.")
            empty.setFlags(empty.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            empty.setForeground(Qt.GlobalColor.gray)
            self.list_widget.addItem(empty)
            return

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == self._active_prompt:
                self.list_widget.setCurrentRow(i)
                break
        self._on_selection_changed()

    def _on_item_clicked(self, name: str):
        self._on_selection_changed()

    def _on_selection_changed(self):
        current = self.list_widget.currentRow()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget is not None and hasattr(widget, "set_selected"):
                widget.set_selected(i == current)

    def _activate(self, name: str):
        self._active_prompt = name
        self.prompt_activated.emit(name)
        self.refresh_list()

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
            save_prompt(name, dialog.result_content())
            self.refresh_list()
            self.prompt_edited.emit()

    def _copy_prompt(self):
        name = self._get_name()
        if not name:
            return
        content = read_prompt(name)
        QApplication.clipboard().setText(content)
        self.copy_btn.setText("OK")
        QApplication.processEvents()
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1200, lambda: self.copy_btn.setText("\u29C9"))

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
                self._active_prompt = ""
            self.refresh_list()
            self.prompt_edited.emit()

    def _use_current(self):
        name = self.current_prompt_name()
        if not name:
            return
        self._activate(name)