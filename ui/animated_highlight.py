from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PyQt6.QtGui import QPainter, QPainterPath, QLinearGradient, QColor


class AnimatedHighlight(QWidget):
    """Resaltado de seleccion con desvanecimiento suave (fade in/out)."""

    def __init__(self, parent=None, radius: int = 10, duration: int = 200):
        super().__init__(parent)
        self._radius = radius
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_selected(self, selected: bool, animate: bool = True):
        self._anim.stop()
        target = 1.0 if selected else 0.0
        if animate:
            self._anim.setStartValue(self._opacity_effect.opacity())
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._opacity_effect.setOpacity(target)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        if rect.width() <= 0 or rect.height() <= 0:
            return
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)

        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, QColor("#1d4ed8"))
        grad.setColorAt(1.0, QColor("#7c3aed"))
        p.fillPath(path, grad)

        p.setPen(QColor(59, 130, 246, 140))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)