from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea,
    QLabel, QFrame, QHBoxLayout, QSizePolicy,
    QPushButton, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtWidgets import QApplication
import time
import os


class ChatMessage(QFrame):
    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self._msg_text = text
        self._setup_ui(text)

    def _setup_ui(self, text: str):
        self.setStyleSheet("background: transparent; border: none;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 4, 14, 4)

        bubble = QFrame()
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        bubble.setMaximumWidth(520)

        if self.is_user:
            bubble.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #2563eb, stop:1 #7c3aed);
                    border-radius: 16px 16px 4px 16px;
                    padding: 2px;
                }
            """)
            layout.addStretch()
            layout.addWidget(bubble, 0)
        else:
            bubble.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #131820, stop:1 #161d2a);
                    border-radius: 16px 16px 16px 4px;
                    padding: 2px;
                    border: 1px solid #1e2a3a;
                }
            """)
            layout.addWidget(bubble, 0)
            layout.addStretch()

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 40))
        bubble.setGraphicsEffect(shadow)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(14, 10, 14, 10)
        bubble_layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        if self.is_user:
            sender = "Tu"
            dot_color = "#60a5fa"
        else:
            sender = "IA"
            dot_color = "#a78bfa"

        dot = QLabel("\u25cf")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 8px; border: none; background: transparent;")
        dot.setFixedWidth(10)
        header_row.addWidget(dot)

        sender_label = QLabel(sender)
        sender_label.setStyleSheet("""
            color: #6b7a90;
            font-size: 10px;
            border: none;
            background: transparent;
            font-weight: 600;
            letter-spacing: 1px;
        """)
        header_row.addWidget(sender_label)
        header_row.addStretch()

        if not self.is_user:
            self._copy_btn = QPushButton("Copiar")
            self._copy_btn.setFixedHeight(24)
            self._copy_btn.setStyleSheet("""
                QPushButton {
                    color: #6b7a90;
                    background: transparent;
                    border: 1px solid #1e2a3a;
                    border-radius: 6px;
                    padding: 3px 10px;
                    font-size: 10px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    color: #c5cdd8;
                    background-color: #1e2a3a;
                    border-color: #3b82f6;
                }
            """)
            self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._copy_btn.clicked.connect(self._copy_text)
            header_row.addWidget(self._copy_btn)

        bubble_layout.addLayout(header_row)

        msg_label = QLabel()
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        msg_label.setStyleSheet("border: none; background: transparent;")
        msg_label.setText(text if text else " ")
        self._msg_label = msg_label
        bubble_layout.addWidget(msg_label)

        if self.is_user:
            time_label = QLabel(time.strftime("%H:%M"))
            time_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 9px; border: none; background: transparent;")
            time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            bubble_layout.addWidget(time_label)

    def _copy_text(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self._msg_text)
        if hasattr(self, '_copy_btn'):
            self._copy_btn.setText("Copiado!")
            self._copy_btn.setStyleSheet("""
                QPushButton {
                    color: white;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #059669, stop:1 #10b981);
                    border: 1px solid #059669;
                    border-radius: 6px;
                    padding: 3px 10px;
                    font-size: 10px;
                    font-weight: 600;
                }
            """)
            QTimer.singleShot(1500, self._reset_copy_btn)

    def _reset_copy_btn(self):
        if hasattr(self, '_copy_btn'):
            self._copy_btn.setText("Copiar")
            self._copy_btn.setStyleSheet("""
                QPushButton {
                    color: #6b7a90;
                    background: transparent;
                    border: 1px solid #1e2a3a;
                    border-radius: 6px;
                    padding: 3px 10px;
                    font-size: 10px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    color: #c5cdd8;
                    background-color: #1e2a3a;
                    border-color: #3b82f6;
                }
            """)

    def set_text(self, text: str):
        self._msg_text = text
        if hasattr(self, '_msg_label'):
            self._msg_label.setText(text if text else " ")

    def append_text(self, text: str):
        self._msg_text += text
        if hasattr(self, '_msg_label'):
            self._msg_label.setText(self._msg_text)


class TypingIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dot_index = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(78, 4, 14, 4)

        bubble = QFrame()
        bubble.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #131820, stop:1 #161d2a);
                border-radius: 16px 16px 16px 4px;
                padding: 2px;
                border: 1px solid #1e2a3a;
            }
        """)
        bubble_layout = QHBoxLayout(bubble)
        bubble_layout.setContentsMargins(16, 12, 16, 12)
        bubble_layout.setSpacing(4)

        self._dots = []
        for i in range(3):
            dot = QLabel("\u25cf")
            dot.setStyleSheet("color: #3b4a6b; font-size: 10px; border: none; background: transparent;")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setFixedWidth(12)
            bubble_layout.addWidget(dot)
            self._dots.append(dot)

        layout.addWidget(bubble)
        layout.addStretch()

        self._timer = QTimer()
        self._timer.timeout.connect(self._animate)
        self._timer.start(400)

    def _animate(self):
        for i, dot in enumerate(self._dots):
            if i == self._dot_index:
                dot.setStyleSheet("color: #3b82f6; font-size: 12px; border: none; background: transparent;")
            else:
                dot.setStyleSheet("color: #3b4a6b; font-size: 10px; border: none; background: transparent;")
        self._dot_index = (self._dot_index + 1) % 3

    def stop(self):
        self._timer.stop()


class ChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chat_area")
        self._messages = []
        self._typing_widget = None
        self._ai_message = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setObjectName("chat_area")
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: #0a0e14; }")

        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(0, 12, 0, 12)
        self.messages_layout.setSpacing(4)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_widget)
        layout.addWidget(self.scroll_area)

    def _add_widget(self, widget):
        count = self.messages_layout.count()
        self.messages_layout.insertWidget(count - 1, widget)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def add_message(self, text: str, is_user: bool = True) -> ChatMessage:
        msg = ChatMessage(text, is_user, self)
        self._add_widget(msg)
        self._messages.append(msg)
        return msg

    def start_ai_message(self):
        self._remove_typing()
        self._typing_widget = TypingIndicator()
        self._add_widget(self._typing_widget)
        self._ai_message = None

    def append_to_last_ai(self, text: str):
        if self._ai_message is None:
            if self._typing_widget:
                self._typing_widget.stop()
                self._typing_widget.deleteLater()
                self._typing_widget = None
            self._ai_message = ChatMessage("", is_user=False, parent=self)
            self._add_widget(self._ai_message)
            self._messages.append(self._ai_message)
        self._ai_message.append_text(text)
        self._scroll_to_bottom()

    def finish_ai_message(self):
        self._remove_typing()
        self._ai_message = None

    def _remove_typing(self):
        if self._typing_widget:
            self._typing_widget.stop()
            self._typing_widget.deleteLater()
            self._typing_widget = None

    def clear_chat(self):
        for msg in self._messages:
            msg.deleteLater()
        self._messages.clear()
        self._ai_message = None
        self._remove_typing()

    def add_file_attachment(self, filename: str, is_user: bool = True):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #131820, stop:1 #1e2a3a);
                border: 1px solid #1e2a3a;
                border-radius: 8px;
                padding: 2px;
            }
        """)
        h_layout = QHBoxLayout(frame)
        h_layout.setContentsMargins(12, 6, 12, 6)
        h_layout.setSpacing(8)

        icon = QLabel("\U0001F4C4")
        icon.setStyleSheet("font-size: 18px; background: transparent; border: none;")
        h_layout.addWidget(icon)

        name_label = QLabel(filename)
        name_label.setStyleSheet("color: #60a5fa; font-size: 11px; background: transparent; border: none; font-weight: 500;")
        h_layout.addWidget(name_label)
        h_layout.addStretch()

        layout_wrapper = QHBoxLayout()
        if is_user:
            layout_wrapper.addStretch()
            layout_wrapper.addWidget(frame, 0)
        else:
            layout_wrapper.addWidget(frame, 0)
            layout_wrapper.addStretch()

        container = QWidget()
        container.setLayout(layout_wrapper)
        self._add_widget(container)

    def add_image_preview(self, pixmap: QPixmap, filename: str):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #131820, stop:1 #161d2a);
                border: 1px solid #1e2a3a;
                border-radius: 10px;
                padding: 6px;
            }
        """)
        v_layout = QVBoxLayout(frame)
        v_layout.setContentsMargins(8, 8, 8, 8)

        img_label = QLabel()
        scaled = pixmap.scaled(320, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        img_label.setPixmap(scaled)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setStyleSheet("border: none; background: transparent; border-radius: 6px;")
        v_layout.addWidget(img_label)

        name_label = QLabel(filename)
        name_label.setStyleSheet("color: #6b7a90; font-size: 10px; border: none; background: transparent;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(name_label)

        layout_wrapper = QHBoxLayout()
        layout_wrapper.addStretch()
        layout_wrapper.addWidget(frame, 0)

        container = QWidget()
        container.setLayout(layout_wrapper)
        self._add_widget(container)
