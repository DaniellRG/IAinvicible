from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea,
    QLabel, QFrame, QHBoxLayout, QSizePolicy,
    QPushButton, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QColor, QFont
from PyQt6.QtWidgets import QApplication
import time
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from utils.markdown import md_to_html


def _is_text_label(widget):
    return isinstance(widget, QLabel)


class ChatMessage(QFrame):
    def __init__(self, text: str, is_user: bool = True, parent=None, streaming: bool = False):
        super().__init__(parent)
        self.is_user = is_user
        self._msg_text = text
        self._streaming = streaming
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
            self._copy_top_btn = self._make_copy_button()
            header_row.addWidget(self._copy_top_btn)

        bubble_layout.addLayout(header_row)

        self._body_widgets = []
        self._parsed = None
        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 4, 0, 0)
        self._body_layout.setSpacing(6)
        self._build_body(text)
        bubble_layout.addWidget(self._body, 1)

        if not self.is_user:
            bottom_row = QHBoxLayout()
            bottom_row.setContentsMargins(0, 2, 0, 0)
            bottom_row.addStretch()
            self._copy_bottom_btn = self._make_copy_button()
            self._copy_bottom_btn.setVisible(not self._streaming)
            bottom_row.addWidget(self._copy_bottom_btn)
            bubble_layout.addLayout(bottom_row)

        if self.is_user:
            time_label = QLabel(time.strftime("%H:%M"))
            time_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 9px; border: none; background: transparent;")
            time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            bubble_layout.addWidget(time_label)

    def _make_copy_button(self):
        btn = QPushButton("Copiar")
        btn.setFixedHeight(24)
        btn.setStyleSheet(self._copy_button_style())
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._copy_text)
        return btn

    @staticmethod
    def _copy_button_style(selected: bool = False):
        if selected:
            return """
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
            """
        return """
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
        """

    def _copy_text(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self._msg_text)
        for attr in ("_copy_top_btn", "_copy_bottom_btn"):
            btn = getattr(self, attr, None)
            if btn is not None:
                btn.setText("Copiado!")
                btn.setStyleSheet(self._copy_button_style(True))
        QTimer.singleShot(1500, self._reset_copy_btn)

    def _reset_copy_btn(self):
        for attr in ("_copy_top_btn", "_copy_bottom_btn"):
            btn = getattr(self, attr, None)
            if btn is not None:
                btn.setText("Copiar")
                btn.setStyleSheet(self._copy_button_style())

    def set_complete(self):
        if not self.is_user:
            btn = getattr(self, "_copy_bottom_btn", None)
            if btn is not None:
                btn.setVisible(True)

    def _build_body(self, text: str):
        from utils.markdown import split_blocks as _split_blocks
        segs = _split_blocks(text)

        if self._parsed == segs:
            return
        if (self._parsed is not None and len(segs) == len(self._parsed)
                and len(segs) > 0 and self._body_widgets):
            same_prefix = all(
                a == b for a, b in zip(self._parsed[:-1], segs[:-1])
            )
            last_new = segs[-1]
            last_old = self._parsed[-1]
            last_widget = self._body_widgets[-1]
            if (same_prefix and last_new[0] == "text" and last_old[0] == "text"
                    and _is_text_label(last_widget)):
                last_widget.setText(self._render_text(last_new[1]))
                self._parsed = segs
                return

        self._clear_body()
        self._parsed = segs
        for seg in segs:
            if seg[0] == "text":
                widget = self._make_text_label(seg[1])
            else:
                widget = self._make_code_card(seg[1], seg[2])
            self._body_layout.addWidget(widget)
            self._body_widgets.append(widget)

    def _clear_body(self):
        for widget in self._body_widgets:
            widget.deleteLater()
        self._body_widgets.clear()

    def _render_text(self, seg: str):
        if self.is_user:
            return seg if seg else " "
        lab = QLabel(seg)
        lab.setTextFormat(Qt.TextFormat.RichText)
        html = md_to_html(seg)
        lab.deleteLater()
        return html

    def _make_text_label(self, seg: str) -> QLabel:
        label = QLabel()
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        label.setStyleSheet("border: none; background: transparent;")
        if self.is_user:
            label.setTextFormat(Qt.TextFormat.PlainText)
        label.setText(self._render_text(seg.rstrip("\n")))
        return label

    def _make_code_card(self, lang: str, code: str) -> QFrame:
        card = QFrame()
        card.setObjectName("code_card")
        card.setStyleSheet("""
            QFrame#code_card {
                background-color: #0d1117;
                border: 1px solid #22303f;
                border-radius: 8px;
            }
        """)
        v = QVBoxLayout(card)
        v.setContentsMargins(10, 6, 10, 8)
        v.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)
        lang_label = QLabel(lang if lang else "c\u00f3digo")
        lang_label.setStyleSheet(
            "color: #7dd3fc; font-size: 10px; font-weight: 600;"
            " border: none; background: transparent;"
        )
        header.addWidget(lang_label)
        header.addStretch()

        copy_btn = QPushButton("Copiar")
        copy_btn.setFixedHeight(22)
        copy_btn.setStyleSheet(self._copy_button_style())
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        def _copy_code():
            QApplication.clipboard().setText(code)
            copy_btn.setText("Copiado!")
            copy_btn.setStyleSheet(self._copy_button_style(True))
            QTimer.singleShot(1600, lambda: (
                copy_btn.setText("Copiar"),
                copy_btn.setStyleSheet(self._copy_button_style()),
            ))

        copy_btn.clicked.connect(_copy_code)
        header.addWidget(copy_btn)
        v.addLayout(header)

        code_label = QLabel(code)
        code_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        code_label.setWordWrap(True)
        code_label.setTextFormat(Qt.TextFormat.PlainText)
        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPixelSize(12)
        code_label.setFont(font)
        code_label.setStyleSheet(
            "color: #d6e2f0; background: transparent; border: none;"
            " font-family: Consolas, 'Courier New', monospace;"
        )
        v.addWidget(code_label)
        return card

    def set_text(self, text: str):
        self._msg_text = text
        self._build_body(text)

    def append_text(self, text: str):
        self._msg_text += text
        self._build_body(self._msg_text)


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
            self._ai_message = ChatMessage("", is_user=False, parent=self, streaming=True)
            self._add_widget(self._ai_message)
            self._messages.append(self._ai_message)
        self._ai_message.append_text(text)
        self._scroll_to_bottom()

    def finish_ai_message(self):
        self._remove_typing()
        if self._ai_message is not None:
            self._ai_message.set_complete()
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
