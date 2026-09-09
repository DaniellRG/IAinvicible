from PyQt6.QtCore import QObject, QEvent


class _TooltipBlocker(QObject):
    """Bloquea todos los tooltips (ventanitas que aparecen al pasar/pulsar)."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.ToolTip:
            return True
        return super().eventFilter(obj, event)


def install_tooltip_blocker(app):
    app.installEventFilter(_TooltipBlocker(app))