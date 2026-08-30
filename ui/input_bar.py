from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QTextEdit, QPushButton, QFrame, QFileDialog,
    QLabel, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QFont, QColor


class InputBar(QWidget):
    message_sent = pyqtSignal(str)
    file_attached = pyqtSignal(str)
    image_attached = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("input_bar")
        self._attached_files = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        self.attachments_row = QHBoxLayout()
        self.attachments_row.setSpacing(6)
        self.attachments_container = QWidget()
        self.attachments_container.setLayout(self.attachments_row)
        self.attachments_container.setVisible(False)
        layout.addWidget(self.attachments_container)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.image_btn = QPushButton("\U0001F5BC")
        self.image_btn.setObjectName("image_btn")
        self.image_btn.setFixedSize(40, 40)
        self.image_btn.setToolTip("Adjuntar imagen")
        self.image_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.image_btn.clicked.connect(self._pick_image)
        input_row.addWidget(self.image_btn)

        self.attach_btn = QPushButton("\U0001F4CE")
        self.attach_btn.setObjectName("attach_btn")
        self.attach_btn.setFixedSize(40, 40)
        self.attach_btn.setToolTip("Adjuntar archivo")
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.clicked.connect(self._pick_file)
        input_row.addWidget(self.attach_btn)

        self.input_field = QTextEdit()
        self.input_field.setObjectName("input_field")
        self.input_field.setPlaceholderText("Escribe tu mensaje...")
        self.input_field.setMaximumHeight(100)
        self.input_field.setMinimumHeight(44)
        self.input_field.setFont(QFont("Segoe UI", 14))
        self.input_field.verticalScrollBar().setVisible(False)
        self.input_field.setAcceptRichText(False)
        self.input_field.installEventFilter(self)
        input_row.addWidget(self.input_field, 1)

        self.send_button = QPushButton("\u27A4")
        self.send_button.setObjectName("send_button")
        self.send_button.setFixedSize(44, 44)
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self._send_message)
        input_row.addWidget(self.send_button)

        layout.addLayout(input_row)

    def eventFilter(self, obj, event):
        if obj == self.input_field and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._send_message()
                return True
        return super().eventFilter(obj, event)

    def _send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text and not self._attached_files:
            return

        for fpath in self._attached_files:
            self.file_attached.emit(fpath)

        if text:
            self.message_sent.emit(text)

        self.input_field.clear()
        self._attached_files.clear()
        self._clear_attachments_ui()
        self.input_field.setFocus()

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo", "",
            "Archivos (*.pdf *.docx *.doc *.txt *.csv *.json *.xml *.py *.js *.html *.css);;Todos (*)"
        )
        if path:
            self._attached_files.append(path)
            self._add_attachment_badge(path)

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen", "",
            "Imagenes (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;Todos (*)"
        )
        if path:
            pixmap = QPixmap(path)
            self.image_attached.emit(path, pixmap)
            self._attached_files.append(path)
            self._add_attachment_badge(path, is_image=True)

    def _add_attachment_badge(self, filepath: str, is_image: bool = False):
        self.attachments_container.setVisible(True)

        badge = QFrame()
        badge.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #131820, stop:1 #1e2a3a);
                border: 1px solid #1e2a3a;
                border-radius: 14px;
                padding: 2px;
            }
        """)
        h = QHBoxLayout(badge)
        h.setContentsMargins(10, 4, 8, 4)
        h.setSpacing(6)

        icon = "\U0001F5BC" if is_image else "\U0001F4C4"
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        h.addWidget(icon_label)

        import os
        name = os.path.basename(filepath)
        if len(name) > 25:
            name = name[:22] + "..."
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #c5cdd8; font-size: 11px; background: transparent; border: none; font-weight: 500;")
        h.addWidget(name_label)

        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                color: #6b7a90; background: transparent; border: none;
                font-size: 11px;
            }
            QPushButton:hover { color: #f87171; }
        """)
        close_btn.clicked.connect(lambda: self._remove_attachment(badge, filepath))
        h.addWidget(close_btn)

        self.attachments_row.addWidget(badge)

    def _remove_attachment(self, badge, filepath):
        if filepath in self._attached_files:
            self._attached_files.remove(filepath)
        badge.deleteLater()
        if not self._attached_files:
            self.attachments_container.setVisible(False)

    def _clear_attachments_ui(self):
        while self.attachments_row.count():
            item = self.attachments_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.attachments_container.setVisible(False)

    def set_enabled(self, enabled: bool):
        self.input_field.setEnabled(enabled)
        self.send_button.setEnabled(enabled)
        self.image_btn.setEnabled(enabled)
        self.attach_btn.setEnabled(enabled)
