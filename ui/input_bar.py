from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QTextEdit, QPushButton, QFrame, QFileDialog,
    QLabel, QSizePolicy, QGraphicsDropShadowEffect, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QFont, QColor

from ui.icon_helpers import (
    IconButton, make_icon, DANGER
)


class InputBar(QWidget):
    message_sent = pyqtSignal(str)
    file_attached = pyqtSignal(str)
    image_attached = pyqtSignal(str, object)
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("input_bar")
        self._attached_files = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        self.attachments_scroll = QScrollArea()
        self.attachments_scroll.setWidgetResizable(True)
        self.attachments_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.attachments_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.attachments_scroll.setFixedHeight(46)
        self.attachments_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.attachments_scroll.horizontalScrollBar().setStyleSheet(
            "QScrollBar:horizontal { background: transparent; height: 4px; margin: 0; }"
            "QScrollBar::handle:horizontal { background: #2d3a4a; border-radius: 2px; min-width: 30px; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }"
            "QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }"
        )
        self.attachments_content = QWidget()
        self.attachments_content.setStyleSheet("background: transparent;")
        self.attachments_row = QHBoxLayout(self.attachments_content)
        self.attachments_row.setContentsMargins(0, 0, 0, 0)
        self.attachments_row.setSpacing(6)
        self.attachments_row.addStretch()
        self.attachments_scroll.setWidget(self.attachments_content)
        self.attachments_scroll.setVisible(False)
        layout.addWidget(self.attachments_scroll, 0, Qt.AlignmentFlag.AlignTop)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.image_btn = IconButton("mdi.image-outline", tooltip="Adjuntar imagen", size=40)
        self.image_btn.clicked.connect(self._pick_image)
        input_row.addWidget(self.image_btn)

        self.attach_btn = IconButton("mdi.paperclip", tooltip="Adjuntar archivo", size=40)
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

        self.send_button = QPushButton()
        self.send_button.setObjectName("send_button")
        self.send_button.setFixedSize(44, 44)
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.setIconSize(QSize(22, 22))
        send_icon = make_icon("mdi.send", "#ffffff")
        if send_icon:
            self.send_button.setIcon(send_icon)
        else:
            self.send_button.setText("\u27A4")
        self.send_button.clicked.connect(self._send_message)

        self.stop_button = QPushButton()
        self.stop_button.setObjectName("stop_button")
        self.stop_button.setFixedSize(44, 44)
        self.stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_button.setToolTip("Detener generacion (Esc)")
        self.stop_button.setIconSize(QSize(18, 18))
        stop_icon = make_icon("mdi.stop", "#f87171")
        if stop_icon:
            self.stop_button.setIcon(stop_icon)
        else:
            self.stop_button.setText("\u25A0")
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.stop_button.hide()
        input_row.addWidget(self.send_button)
        input_row.addWidget(self.stop_button)

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
        self.attachments_scroll.setVisible(True)

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

        close_btn = IconButton("mdi.close", tooltip="Quitar", size=22,
                               variant="danger", hover_color=DANGER)
        close_btn.clicked.connect(lambda: self._remove_attachment(badge, filepath))
        h.addWidget(close_btn)

        self.attachments_row.insertWidget(self.attachments_row.count() - 1, badge)

    def _remove_attachment(self, badge, filepath):
        if filepath in self._attached_files:
            self._attached_files.remove(filepath)
        badge.deleteLater()
        if not self._attached_files:
            self.attachments_scroll.setVisible(False)

    def _clear_attachments_ui(self):
        while self.attachments_row.count() > 1:
            item = self.attachments_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.attachments_scroll.setVisible(False)

    def set_enabled(self, enabled: bool):
        self.input_field.setEnabled(enabled)
        self.send_button.setEnabled(enabled)
        self.image_btn.setEnabled(enabled)
        self.attach_btn.setEnabled(enabled)

    def show_stop(self, show: bool):
        self.stop_button.setVisible(show)
