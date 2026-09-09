from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor

try:
    import qtawesome as qta
    _HAS_QTA = True
except Exception:
    qta = None
    _HAS_QTA = False

BLUE = "#3b82f6"
GRAY = "#6b7a90"
WHITE = "#ffffff"
DANGER = "#ef4444"
GREEN = "#10b981"
AMBER = "#f59e0b"

FALLBACK_GLYPHS = {
    "mdi.plus": "+",
    "mdi.pencil-outline": "\u270e",
    "mdi.content-copy": "\u29c9",
    "mdi.play": "\u25b6",
    "mdi.trash-can-outline": "\U0001F5D1",
    "mdi.close": "\u2715",
    "mdi.paperclip": "\U0001F4CE",
    "mdi.image-outline": "\U0001F5BC",
    "mdi.send": "\u27a4",
    "mdi.stop": "\u25a0",
    "mdi.check": "\u2713",
    "mdi.magnify": "\U0001F50D",
    "mdi.folder-open-outline": "\U0001F4C2",
    "mdi.chat-outline": "\U0001F4AC",
    "mdi.pencil-box-outline": "\u270E",
}

_ICON_CACHE = {}


def make_icon(name, color=GRAY):
    if not _HAS_QTA:
        return None
    key = (name, color)
    if key not in _ICON_CACHE:
        try:
            _ICON_CACHE[key] = qta.icon(name, color=color)
        except Exception:
            _ICON_CACHE[key] = None
    return _ICON_CACHE[key]


_STYLES = {
    "default": (
        "QPushButton { background: transparent; border: none; border-radius: 8px; }"
        "QPushButton:hover { background: rgba(59,130,246,0.13); }"
        "QPushButton:pressed { background: rgba(59,130,246,0.22); }"
    ),
    "danger": (
        "QPushButton { background: transparent; border: none; border-radius: 8px; }"
        "QPushButton:hover { background: rgba(239,68,68,0.16); }"
        "QPushButton:pressed { background: rgba(239,68,68,0.26); }"
    ),
    "action": (
        "QPushButton { background: rgba(59,130,246,0.10); border: none; border-radius: 14px; }"
        "QPushButton:hover { background: rgba(59,130,246,0.24); }"
        "QPushButton:pressed { background: rgba(59,130,246,0.34); }"
    ),
}


class IconButton(QPushButton):
    """Boton de icono vectorial moderno (sin 'caja roja' al pasar el mouse)."""

    def __init__(self, icon_name="", text="", tooltip="", size=28, variant="default",
                 base_color=GRAY, hover_color=BLUE, disabled_color="#3d4a5d", parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._base = base_color
        self._hover = hover_color
        self._disabled = disabled_color
        self.setObjectName("icon_btn")
        self.setStyleSheet(_STYLES.get(variant, _STYLES["default"]))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)

        if text:
            self.setText(text)
            self.setFixedHeight(size)
            self.setFixedWidth(max(size + 16, 30 + len(text) * 8))
            self.setIconSize(QSize(16, 16))
        else:
            self.setFixedSize(size, size)
            self.setIconSize(QSize(int(size * 0.58), int(size * 0.58)))

        if icon_name:
            self.set_icon(icon_name)

    def _apply_state(self):
        color = self._base if self.isEnabled() else self._disabled
        icon = make_icon(self._icon_name, color)
        if icon:
            self.setIcon(icon)
        elif self._icon_name in FALLBACK_GLYPHS:
            self.setText(FALLBACK_GLYPHS[self._icon_name])
            self.setStyleSheet(
                "QPushButton { background: transparent; border: none; border-radius: 8px; color: %s; font-size: 14px; }"
                "QPushButton:hover { background: rgba(59,130,246,0.13); }" % (color if self.isEnabled() else self._disabled)
            )

    def set_icon(self, name, color=None):
        self._icon_name = name
        if color:
            self._base = color
        self._apply_state()

    def flash_icon(self, name, color):
        """Muestra un icono temporal (p.ej. check verde) sin cambiar el estado base."""
        icon = make_icon(name, color)
        if icon:
            self.setIcon(icon)

    def set_colors(self, base, hover):
        self._base = base
        self._hover = hover
        self._apply_state()

    def enterEvent(self, event):
        if self.isEnabled() and self._icon_name:
            icon = make_icon(self._icon_name, self._hover)
            if icon:
                self.setIcon(icon)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isEnabled():
            self._apply_state()
        super().leaveEvent(event)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self._apply_state()