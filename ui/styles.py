DARK_THEME = """
/* ==========================================
   NEXUS DARK - UI Premium
   ========================================== */

QWidget {
    background-color: #0a0e14;
    color: #c5cdd8;
    font-family: 'Segoe UI Variable', 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0a0e14;
}

/* ==========================================
   HEADER / TOOLBAR
   ========================================== */
#header_bar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0d1117, stop:0.5 #131820, stop:1 #0d1117);
    border-bottom: 1px solid #1b2230;
    padding: 8px 14px;
}

#model_combo {
    background-color: #131820;
    color: #c5cdd8;
    border: 1px solid #1e2a3a;
    border-radius: 10px;
    padding: 7px 14px;
    min-width: 240px;
    font-size: 12px;
    font-weight: 500;
}

#model_combo:hover {
    border-color: #3b82f6;
    background-color: #161d2a;
}

#model_combo:focus {
    border-color: #3b82f6;
    background-color: #161d2a;
}

#model_combo::drop-down {
    border: none;
    width: 28px;
    subcontrol-position: center right;
}

#model_combo::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #6b7a90;
    margin-right: 8px;
}

#model_combo QAbstractItemView {
    background-color: #131820;
    color: #c5cdd8;
    selection-background-color: #1d4ed8;
    selection-color: white;
    border: 1px solid #1e2a3a;
    border-radius: 8px;
    padding: 6px;
    outline: none;
}

#model_combo QAbstractItemView::item {
    padding: 8px 12px;
    border-radius: 6px;
    min-height: 20px;
}

#model_combo QAbstractItemView::item:hover {
    background-color: #1e2a3a;
}

#status_label {
    color: #6b7a90;
    font-size: 11px;
    padding-left: 6px;
    font-weight: 500;
}

#status_dot {
    font-size: 15px;
    padding: 0px 4px;
}

/* ==========================================
   CHAT AREA
   ========================================== */
#chat_area {
    background-color: #0a0e14;
    border: none;
}

QScrollBar:vertical {
    background-color: transparent;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #1e2a3a;
    border-radius: 5px;
    min-height: 40px;
    border: 2px solid transparent;
}

QScrollBar::handle:vertical:hover {
    background-color: #3b82f6;
    border: 2px solid #0a0e14;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* ==========================================
   INPUT AREA
   ========================================== */
#input_bar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0d1117, stop:1 #0a0e14);
    border-top: 1px solid #1b2230;
    padding: 12px;
}

#input_field {
    background-color: #131820;
    color: #c5cdd8;
    border: 2px solid #1e2a3a;
    border-radius: 12px;
    padding: 12px 16px;
    font-size: 14px;
    min-height: 20px;
    selection-background-color: #3b82f6;
}

#input_field:focus {
    border-color: #3b82f6;
    background-color: #161d2a;
}

#send_button {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #2563eb, stop:1 #7c3aed);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 10px 24px;
    font-weight: bold;
    font-size: 15px;
    min-width: 50px;
}

#send_button:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #3b82f6, stop:1 #8b5cf6);
}

#send_button:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1d4ed8, stop:1 #6d28d9);
}

#send_button:disabled {
    background-color: #1e2a3a;
    color: #4a5568;
}

#attach_btn, #image_btn {
    background-color: transparent;
    color: #6b7a90;
    border: none;
    border-radius: 8px;
    padding: 8px;
    font-size: 18px;
}

#attach_btn:hover, #image_btn:hover {
    color: #3b82f6;
    background-color: #1e2a3a;
}

/* ==========================================
   CHAT MESSAGES - USER
   ========================================== */
.user_msg {
    background-color: #1d4ed8;
    color: #ffffff;
    border-radius: 16px 16px 4px 16px;
    padding: 12px 16px;
    margin: 4px 60px 4px 100px;
}

/* ==========================================
   CHAT MESSAGES - AI
   ========================================== */
.ai_msg {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #131820, stop:1 #161d2a);
    color: #c5cdd8;
    border-radius: 16px 16px 16px 4px;
    padding: 12px 16px;
    margin: 4px 100px 4px 60px;
    border: 1px solid #1e2a3a;
}

/* ==========================================
   ATTACHMENTS
   ========================================== */
.attachment_badge {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #131820, stop:1 #1e2a3a);
    color: #60a5fa;
    border: 1px solid #1e2a3a;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 11px;
}

/* ==========================================
   TYPING INDICATOR
   ========================================== */
#typing_indicator {
    color: #6b7a90;
    font-style: italic;
    font-size: 12px;
    padding: 6px 12px;
}

/* ==========================================
   LABELS
   ========================================== */
QLabel {
    color: #c5cdd8;
}

/* ==========================================
   TOOL BUTTONS
   ========================================== */
QToolButton {
    background-color: transparent;
    color: #6b7a90;
    border: none;
    padding: 6px;
}

QToolButton:hover {
    color: #c5cdd8;
}

/* ==========================================
   COPY BUTTON
   ========================================== */
.copy_btn {
    background-color: transparent;
    color: #6b7a90;
    border: 1px solid #1e2a3a;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 500;
}
.copy_btn:hover {
    color: #c5cdd8;
    background-color: #1e2a3a;
    border-color: #3b82f6;
}
.copy_btn:pressed {
    background-color: #3b82f6;
    color: white;
    border-color: #3b82f6;
}
.copy_btn_copied {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #059669, stop:1 #10b981);
    color: white;
    border: 1px solid #059669;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 500;
}

/* ==========================================
   HISTORY SIDEBAR
   ========================================== */
#history_sidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0d1117, stop:1 #0a0e14);
    border-right: 1px solid #1b2230;
}

#history_item {
    background-color: transparent;
    color: #c5cdd8;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
}

#history_item:hover {
    background-color: #1e2a3a;
}

#history_item_selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1d4ed8, stop:1 #7c3aed);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
}

#history_delete_btn {
    background-color: transparent;
    color: #6b7a90;
    border: none;
    border-radius: 6px;
    padding: 3px 6px;
    font-size: 11px;
}
#history_delete_btn:hover {
    color: #f87171;
    background-color: #1e2a3a;
}

/* ==========================================
   DIALOGS
   ========================================== */
QDialog {
    background-color: #0d1117;
    color: #c5cdd8;
}

QMessageBox {
    background-color: #0d1117;
}

QMessageBox QLabel {
    color: #c5cdd8;
}

QMessageBox QPushButton {
    background-color: #1e2a3a;
    color: #c5cdd8;
    border: 1px solid #2d3a4a;
    border-radius: 6px;
    padding: 6px 16px;
}

QMessageBox QPushButton:hover {
    background-color: #3b82f6;
    border-color: #3b82f6;
}

/* ==========================================
   SPLITTER
   ========================================== */
QSplitter::handle {
    background-color: #1b2230;
    width: 1px;
}

QSplitter::handle:hover {
    background-color: #3b82f6;
}

/* ==========================================
   COMBO BOX POPUP
   ========================================== */
QComboBox QAbstractItemView {
    background-color: #131820;
    border: 1px solid #1e2a3a;
    border-radius: 8px;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    padding: 8px 12px;
    border-radius: 6px;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #1d4ed8;
    color: white;
}
"""


LIGHT_THEME = """
/* ==========================================
   NEXUS LIGHT - UI Premium
   ========================================== */

QWidget {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: 'Segoe UI Variable', 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #f8fafc;
}

/* ==========================================
   HEADER / TOOLBAR
   ========================================== */
#header_bar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ffffff, stop:0.5 #f1f5f9, stop:1 #ffffff);
    border-bottom: 1px solid #e2e8f0;
    padding: 8px 14px;
}

#model_combo {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 7px 14px;
    min-width: 240px;
    font-size: 12px;
    font-weight: 500;
}

#model_combo:hover {
    border-color: #2563eb;
    background-color: #f8fafc;
}

#model_combo:focus {
    border-color: #2563eb;
    background-color: #ffffff;
}

#model_combo::drop-down {
    border: none;
    width: 28px;
}

#model_combo::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #94a3b8;
    margin-right: 8px;
}

#model_combo QAbstractItemView {
    background-color: #ffffff;
    color: #1e293b;
    selection-background-color: #2563eb;
    selection-color: white;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 6px;
    outline: none;
}

#model_combo QAbstractItemView::item {
    padding: 8px 12px;
    border-radius: 6px;
    min-height: 20px;
}

#model_combo QAbstractItemView::item:hover {
    background-color: #f1f5f9;
}

#status_label {
    color: #94a3b8;
    font-size: 11px;
    padding-left: 6px;
    font-weight: 500;
}

#status_dot {
    font-size: 15px;
    padding: 0px 4px;
}

/* ==========================================
   CHAT AREA
   ========================================== */
#chat_area {
    background-color: #f8fafc;
    border: none;
}

QScrollBar:vertical {
    background-color: transparent;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    border-radius: 5px;
    min-height: 40px;
    border: 2px solid transparent;
}

QScrollBar::handle:vertical:hover {
    background-color: #2563eb;
    border: 2px solid #f8fafc;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* ==========================================
   INPUT AREA
   ========================================== */
#input_bar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #f8fafc);
    border-top: 1px solid #e2e8f0;
    padding: 12px;
}

#input_field {
    background-color: #ffffff;
    color: #1e293b;
    border: 2px solid #e2e8f0;
    border-radius: 12px;
    padding: 12px 16px;
    font-size: 14px;
    min-height: 20px;
    selection-background-color: #2563eb;
}

#input_field:focus {
    border-color: #2563eb;
    background-color: #ffffff;
}

#send_button {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #2563eb, stop:1 #7c3aed);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 10px 24px;
    font-weight: bold;
    font-size: 15px;
    min-width: 50px;
}

#send_button:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #3b82f6, stop:1 #8b5cf6);
}

#send_button:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1d4ed8, stop:1 #6d28d9);
}

#send_button:disabled {
    background-color: #e2e8f0;
    color: #94a3b8;
}

#attach_btn, #image_btn {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    padding: 8px;
    font-size: 18px;
}

#attach_btn:hover, #image_btn:hover {
    color: #2563eb;
    background-color: #f1f5f9;
}

/* ==========================================
   CHAT MESSAGES - USER
   ========================================== */
.user_msg {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #2563eb, stop:1 #7c3aed);
    color: #ffffff;
    border-radius: 16px 16px 4px 16px;
    padding: 12px 16px;
    margin: 4px 60px 4px 100px;
}

/* ==========================================
   CHAT MESSAGES - AI
   ========================================== */
.ai_msg {
    background-color: #ffffff;
    color: #1e293b;
    border-radius: 16px 16px 16px 4px;
    padding: 12px 16px;
    margin: 4px 100px 4px 60px;
    border: 1px solid #e2e8f0;
}

/* ==========================================
   ATTACHMENTS
   ========================================== */
.attachment_badge {
    background-color: #f1f5f9;
    color: #2563eb;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 11px;
}

/* ==========================================
   TYPING INDICATOR
   ========================================== */
#typing_indicator {
    color: #94a3b8;
    font-style: italic;
    font-size: 12px;
    padding: 6px 12px;
}

/* ==========================================
   LABELS
   ========================================== */
QLabel {
    color: #1e293b;
}

/* ==========================================
   TOOL BUTTONS
   ========================================== */
QToolButton {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    padding: 6px;
}

QToolButton:hover {
    color: #1e293b;
}

/* ==========================================
   COPY BUTTON
   ========================================== */
.copy_btn {
    background-color: transparent;
    color: #94a3b8;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 500;
}
.copy_btn:hover {
    color: #1e293b;
    background-color: #f1f5f9;
    border-color: #2563eb;
}
.copy_btn:pressed {
    background-color: #2563eb;
    color: white;
    border-color: #2563eb;
}
.copy_btn_copied {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #059669, stop:1 #10b981);
    color: white;
    border: 1px solid #059669;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 500;
}

/* ==========================================
   HISTORY SIDEBAR
   ========================================== */
#history_sidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #f8fafc);
    border-right: 1px solid #e2e8f0;
}

#history_item {
    background-color: transparent;
    color: #1e293b;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
}

#history_item:hover {
    background-color: #f1f5f9;
}

#history_item_selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2563eb, stop:1 #7c3aed);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
}

#history_delete_btn {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 6px;
    padding: 3px 6px;
    font-size: 11px;
}
#history_delete_btn:hover {
    color: #ef4444;
    background-color: #f1f5f9;
}

/* ==========================================
   DIALOGS
   ========================================== */
QDialog {
    background-color: #ffffff;
    color: #1e293b;
}

QMessageBox {
    background-color: #ffffff;
}

QMessageBox QLabel {
    color: #1e293b;
}

QMessageBox QPushButton {
    background-color: #f1f5f9;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 6px 16px;
}

QMessageBox QPushButton:hover {
    background-color: #2563eb;
    border-color: #2563eb;
    color: white;
}

/* ==========================================
   SPLITTER
   ========================================== */
QSplitter::handle {
    background-color: #e2e8f0;
    width: 1px;
}

QSplitter::handle:hover {
    background-color: #2563eb;
}

/* ==========================================
   COMBO BOX POPUP
   ========================================== */
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    padding: 8px 12px;
    border-radius: 6px;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #2563eb;
    color: white;
}
"""

THEMES = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}


def get_theme(name: str = "dark") -> str:
    return THEMES.get(name, DARK_THEME)
