from __future__ import annotations

import json
import math
import os
import platform
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

from PyQt6.QtCore import (
    QEasingCurve, QEvent, QMimeData, QObject, QPointF, QRect, QRectF, QSize, Qt,
    QTimer, QUrl, pyqtSignal, QPropertyAnimation,
)
from PyQt6.QtGui import (
    QBrush, QColor, QDragEnterEvent, QDropEvent, QFont, QFontDatabase,
    QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient, QShortcut, QSurfaceFormat, QGuiApplication, QRegion,
    QPalette,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget, QProgressBar, QGraphicsOpacityEffect,
)

# Setup surface format for clean Wayland / OpenGL premultiplied alpha
_fmt = QSurfaceFormat()
_fmt.setAlphaBufferSize(8)
_fmt.setDepthBufferSize(0)
_fmt.setSamples(4)
_fmt.setSwapInterval(1)
QSurfaceFormat.setDefaultFormat(_fmt)

def setup_dark_app_theme(app: QApplication | None = None):
    """Enforces high-contrast luminous cyber-dark theme across all standard dialogs and widgets."""
    if not app:
        app = QApplication.instance()
    if not app:
        return
    app.setStyle("Fusion")
    pal = QPalette()
    # Window & Base
    pal.setColor(QPalette.ColorRole.Window, QColor(11, 21, 34))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(224, 246, 252))
    pal.setColor(QPalette.ColorRole.Base, QColor(8, 16, 26))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(14, 27, 43))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(11, 21, 34))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(224, 246, 252))
    # Text
    pal.setColor(QPalette.ColorRole.Text, QColor(224, 246, 252))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(90, 184, 204))
    # Buttons
    pal.setColor(QPalette.ColorRole.Button, QColor(15, 34, 54))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(224, 246, 252))
    pal.setColor(QPalette.ColorRole.BrightText, QColor(255, 80, 100))
    # Highlights
    pal.setColor(QPalette.ColorRole.Highlight, QColor(0, 180, 230))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(pal)

    app.setStyleSheet("""
        QFileDialog {
            background-color: #0b1522;
            color: #e0f6fc;
        }
        QFileDialog QWidget {
            color: #e0f6fc;
        }
        QFileDialog QListView, QFileDialog QTreeView {
            background-color: #08101a;
            color: #e0f6fc;
            border: 1px solid #1a334d;
            selection-background-color: #007a99;
            selection-color: #ffffff;
        }
        QFileDialog QLineEdit, QFileDialog QComboBox {
            background-color: #0c1c2e;
            color: #e0f6fc;
            border: 1px solid #1a5c7a;
            border-radius: 4px;
            padding: 4px 8px;
        }
        QFileDialog QPushButton {
            background-color: #0f2a42;
            color: #00d4ff;
            border: 1px solid #1a5c7a;
            border-radius: 4px;
            padding: 4px 12px;
        }
        QFileDialog QPushButton:hover {
            background-color: #143d60;
            border: 1px solid #00d4ff;
            color: #ffffff;
        }
        QFileDialog QHeaderView::section {
            background-color: #0e2238;
            color: #59d4e6;
            border: 1px solid #1a334d;
            padding: 4px;
        }
    """)

from orion_visage import OrionParticleCanvas
HudCanvas = OrionParticleCanvas

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

_DEFAULT_W, _DEFAULT_H = 980, 700
_MIN_W,     _MIN_H     = 820, 580
_LEFT_W  = 148
_RIGHT_W = 340

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


class C:
    BG        = "#00060a"
    PANEL     = "#010d14"
    PANEL2    = "#010f18"
    BORDER    = "#0d3347"
    BORDER_B  = "#1a5c7a"
    BORDER_A  = "#0f4060"
    PRI       = "#00d4ff"
    PRI_DIM   = "#007a99"
    PRI_GHO   = "#001f2e"
    ACC       = "#ff6b00"
    ACC2      = "#ffcc00"
    GREEN     = "#00ff88"
    GREEN_D   = "#00aa55"
    RED       = "#ff3355"
    MUTED_C   = "#ff3366"
    TEXT      = "#8ffcff"
    TEXT_DIM  = "#3a8a9a"
    TEXT_MED  = "#5ab8cc"
    WHITE     = "#d8f8ff"
    DARK      = "#000d14"
    BAR_BG    = "#011520"


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h); c.setAlpha(a); return c

class _SysMetrics:
    """Lazy on-demand metrics snapshot provider."""
    def snapshot(self) -> dict:
        try:
            from actions.vitals import collect_system_vitals
            v = collect_system_vitals()
            return {
                "cpu": v["cpu"]["percent"],
                "mem": v["memory"]["percent"],
                "net": 0.0,
                "gpu": v["gpu"]["util_pct"],
                "tmp": v["cpu"]["temp_c"]
            }
        except Exception:
            return {"cpu": 0.0, "mem": 0.0, "net": 0.0, "gpu": -1.0, "tmp": -1.0}


_metrics = _SysMetrics()


class VitalsToastOverlay(QFrame):
    """Floating translucent toast overlay presenting instantaneous hardware vitals."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VitalsToast")
        self.setStyleSheet("""
            QFrame#VitalsToast {
                background-color: rgba(2, 12, 22, 215);
                border: 1px solid rgba(0, 212, 255, 120);
                border-radius: 8px;
            }
            QLabel {
                color: #8ffcff;
                font-family: 'Courier New', monospace;
                background: transparent;
                border: none;
            }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(10)

        self._cpu_lbl = QLabel("CPU --%")
        self._cpu_lbl.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._cpu_lbl.setStyleSheet("color: #00d4ff;")
        lay.addWidget(self._cpu_lbl)

        sep1 = QLabel("·")
        sep1.setStyleSheet("color: #0d3347;")
        lay.addWidget(sep1)

        self._mem_lbl = QLabel("RAM --%")
        self._mem_lbl.setFont(QFont("Courier New", 8))
        self._mem_lbl.setStyleSheet("color: #00ff88;")
        lay.addWidget(self._mem_lbl)

        sep2 = QLabel("·")
        sep2.setStyleSheet("color: #0d3347;")
        lay.addWidget(sep2)

        self._gpu_lbl = QLabel("GPU --%")
        self._gpu_lbl.setFont(QFont("Courier New", 8))
        self._gpu_lbl.setStyleSheet("color: #ffcc00;")
        lay.addWidget(self._gpu_lbl)

        sep3 = QLabel("·")
        sep3.setStyleSheet("color: #0d3347;")
        lay.addWidget(sep3)

        self._tmp_lbl = QLabel("TMP --°C")
        self._tmp_lbl.setFont(QFont("Courier New", 8))
        self._tmp_lbl.setStyleSheet("color: #ff6688;")
        lay.addWidget(self._tmp_lbl)

        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0.0)

        self._hide_tmr = QTimer(self)
        self._hide_tmr.setSingleShot(True)
        self._hide_tmr.timeout.connect(self._fade_out)

        self.hide()

    def display(self, data: dict):
        cpu_p = data.get("cpu", {}).get("percent", 0.0)
        cpu_t = data.get("cpu", {}).get("temp_c", -1.0)
        mem_p = data.get("memory", {}).get("percent", 0.0)
        gpu = data.get("gpu", {})
        gpu_p = gpu.get("util_pct", -1.0)
        gpu_t = gpu.get("temp_c", -1.0)

        self._cpu_lbl.setText(f"CPU {cpu_p:.0f}%")
        self._mem_lbl.setText(f"RAM {mem_p:.0f}%")
        self._gpu_lbl.setText(f"GPU {gpu_p:.0f}%" if gpu.get("available") and gpu_p >= 0 else "GPU N/A")

        tmp = cpu_t if cpu_t > 0 else gpu_t
        self._tmp_lbl.setText(f"TMP {tmp:.0f}°C" if tmp > 0 else "TMP --°C")

        self.show()
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(220)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

        self._hide_tmr.start(6000)

    def _fade_out(self):
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(350)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.hide)
        self._anim.start()


class GlassHeaderWidget(QWidget):
    """Glassmorphic header with live clock, subtle title, and window controls."""

    minimize_clicked = pyqtSignal()
    maximize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassHeader")
        self.setFixedHeight(42)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("""
            QWidget#GlassHeader {
                background-color: rgba(2, 10, 18, 0.40);
                border: 1px solid rgba(0, 212, 255, 0.28);
                border-radius: 8px;
            }
            QLabel {
                color: #59d4e6;
                font-family: 'Courier New', monospace;
                background: transparent;
                border: none;
            }
            QPushButton.WinCtrlBtn {
                background: transparent;
                color: #59d4e6;
                border: 1px solid rgba(0, 212, 255, 0.25);
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                font-weight: bold;
                min-width: 26px;
                max-width: 26px;
                min-height: 24px;
                max-height: 24px;
            }
            QPushButton.WinCtrlBtn:hover {
                background-color: rgba(0, 212, 255, 0.25);
                color: #ffffff;
                border: 1px solid #00d4ff;
            }
            QPushButton#CloseBtn:hover {
                background-color: rgba(255, 51, 85, 0.55);
                border: 1px solid #ff3355;
                color: #ffffff;
            }
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 10, 0)
        lay.setSpacing(8)

        title = QLabel("◈ O.R.I.O.N")
        title.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #00d4ff; letter-spacing: 1px;")
        lay.addWidget(title)

        sub = QLabel("MARK I")
        sub.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        sub.setStyleSheet("color: #00d4ff;")
        lay.addWidget(sub)

        lay.addStretch()

        self._clock_lbl = QLabel("00:00:00")
        self._clock_lbl.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        self._clock_lbl.setStyleSheet("color: #00d4ff;")
        lay.addWidget(self._clock_lbl)

        self._date_lbl = QLabel("")
        self._date_lbl.setFont(QFont("Courier New", 7))
        self._date_lbl.setStyleSheet("color: #7ec7d8;")
        lay.addWidget(self._date_lbl)

        lay.addSpacing(12)

        btn_min = QPushButton("–", self)
        btn_min.setObjectName("MinBtn")
        btn_min.setProperty("class", "WinCtrlBtn")
        btn_min.setToolTip("Collapse to Orb")
        btn_min.clicked.connect(self.minimize_clicked.emit)
        lay.addWidget(btn_min)

        btn_max = QPushButton("□", self)
        btn_max.setObjectName("MaxBtn")
        btn_max.setProperty("class", "WinCtrlBtn")
        btn_max.setToolTip("Maximize / Restore")
        btn_max.clicked.connect(self.maximize_clicked.emit)
        lay.addWidget(btn_max)

        btn_close = QPushButton("✕", self)
        btn_close.setObjectName("CloseBtn")
        btn_close.setProperty("class", "WinCtrlBtn")
        btn_close.setToolTip("Close to Background")
        btn_close.clicked.connect(self.close_clicked.emit)
        lay.addWidget(btn_close)

        self._press_pos = None

    def tick(self):
        self._clock_lbl.setText(time.strftime("%H:%M:%S"))
        self._date_lbl.setText(time.strftime("%a %d %b"))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_clicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is not None:
            delta = event.globalPosition().toPoint() - self._press_pos
            if delta.manhattanLength() >= 4:
                win = self.window()
                wh = win.windowHandle()
                if wh and QGuiApplication.platformName() == "wayland":
                    wh.startSystemMove()
                    self._press_pos = None
                    return
                win.move(win.frameGeometry().topLeft() + delta)
                self._press_pos = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_pos = None
        super().mouseReleaseEvent(event)


class MetricBar(QWidget):
    def __init__(self, label: str = "", color: str = C.PRI, parent=None):
        super().__init__(parent)
    def set_value(self, pct: float, text: str):
        pass


class LogWidget(QTextEdit):
    _sig = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Courier New", 9))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(0, 15, 30, 0.15);
                color: {C.TEXT};
                border: 1px solid rgba(0, 212, 255, 0.22);
                border-radius: 4px;
                padding: 6px;
                selection-background-color: {C.PRI_GHO};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(0, 212, 255, 0.28);
                border-radius: 3px;
                min-height: 20px;
            }}
        """)
        self._queue: list[str] = []
        self._typing  = False
        self._text    = ""
        self._pos     = 0
        self._tag     = "sys"
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._sig.connect(self._enqueue)

    def append_log(self, text: str):
        self._sig.emit(text)

    def _enqueue(self, text: str):
        self._queue.append(text)
        if not self._typing:
            self._next()

    def _next(self):
        if not self._queue:
            self._typing = False
            return
        self._typing = True
        self._text   = self._queue.pop(0)
        self._pos    = 0
        tl = self._text.lower()
        if   tl.startswith("you:"):    self._tag = "you"
        elif tl.startswith("orion:"): self._tag = "ai"
        elif tl.startswith("file:"):   self._tag = "file"
        elif "err" in tl:              self._tag = "err"
        else:                          self._tag = "sys"
        self._tmr.start(6)

    def _step(self):
        if self._pos < len(self._text):
            ch  = self._text[self._pos]
            cur = self.textCursor()
            fmt = cur.charFormat()
            col = {
                "you":  qcol(C.WHITE),
                "ai":   qcol(C.PRI),
                "err":  qcol(C.RED),
                "file": qcol(C.GREEN),
                "sys":  qcol(C.ACC2),
            }.get(self._tag, qcol(C.TEXT))
            fmt.setForeground(QBrush(col))
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText(ch, fmt)
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            self._pos += 1
        else:
            self._tmr.stop()
            cur = self.textCursor()
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText("\n")
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            QTimer.singleShot(20, self._next)

_FILE_ICONS = {
    "image":   ("🖼", "#00d4ff"), "video":   ("🎬", "#ff6b00"),
    "audio":   ("🎵", "#cc44ff"), "pdf":     ("📄", "#ff4444"),
    "word":    ("📝", "#4488ff"), "excel":   ("📊", "#44bb44"),
    "code":    ("💻", "#ffcc00"), "archive": ("📦", "#ff8844"),
    "pptx":    ("📊", "#ff6622"), "text":    ("📃", "#aaaaaa"),
    "data":    ("🔧", "#88ddff"), "unknown": ("📎", "#888888"),
}
_EXT_TO_CAT = {
    **dict.fromkeys(["jpg","jpeg","png","gif","webp","bmp","tiff","svg","ico"], "image"),
    **dict.fromkeys(["mp4","avi","mov","mkv","wmv","flv","webm","m4v"],         "video"),
    **dict.fromkeys(["mp3","wav","ogg","m4a","aac","flac","wma","opus"],        "audio"),
    **dict.fromkeys(["pdf"],                                                     "pdf"),
    **dict.fromkeys(["doc","docx"],                                              "word"),
    **dict.fromkeys(["xls","xlsx","ods"],                                        "excel"),
    **dict.fromkeys(["ppt","pptx"],                                              "pptx"),
    **dict.fromkeys(["py","js","ts","jsx","tsx","html","css","java","c","cpp",
                     "cs","go","rs","rb","php","swift","kt","sh","sql","lua"],   "code"),
    **dict.fromkeys(["zip","rar","tar","gz","7z","bz2","xz"],                   "archive"),
    **dict.fromkeys(["txt","md","rst","log"],                                    "text"),
    **dict.fromkeys(["csv","tsv","json","xml"],                                  "data"),
}

def _file_category(path: Path) -> str:
    return _EXT_TO_CAT.get(path.suffix.lower().lstrip("."), "unknown")

def _fmt_size(size: int) -> str:
    if   size < 1024:    return f"{size} B"
    elif size < 1024**2: return f"{size/1024:.1f} KB"
    elif size < 1024**3: return f"{size/1024**2:.1f} MB"
    else:                return f"{size/1024**3:.1f} GB"


class FileDropZone(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(100)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")
        self._current_file: str | None = None
        self._hovering  = False
        self._drag_over = False
        self._dash_offset = 0.0
        self._anim_tmr = QTimer(self)
        self._anim_tmr.timeout.connect(self._animate)
        self._anim_tmr.start(40)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._canvas = _DropCanvas(self)
        layout.addWidget(self._canvas)

    def _animate(self):
        self._dash_offset = (self._dash_offset + 0.8) % 20
        self._canvas.update()

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._drag_over = True; self._canvas.update()

    def dragLeaveEvent(self, e):
        self._drag_over = False; self._canvas.update()

    def dropEvent(self, e: QDropEvent):
        self._drag_over = False
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_file():
                self._set_file(path)
        self._canvas.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._browse()

    def enterEvent(self, e):
        self._hovering = True; self._canvas.update()

    def leaveEvent(self, e):
        self._hovering = False; self._canvas.update()

    def current_file(self) -> str | None:
        return self._current_file

    def clear_file(self):
        self._current_file = None; self._canvas.update()

    def _browse(self):
        parent_win = self.window()
        # Decouple from parent window surface so Wayland cosmic-comp does not link
        # the dialog as a modal sub-surface that causes transient configure collapse.
        dlg = QFileDialog(None, "Select a file for O.R.I.O.N", str(Path.home()))
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        dlg.setNameFilter(
            "All Files (*.*);;"
            "Images (*.jpg *.jpeg *.png *.gif *.webp *.bmp *.svg);;"
            "Documents (*.pdf *.docx *.txt *.md *.pptx);;"
            "Data (*.csv *.xlsx *.json *.xml);;"
            "Code (*.py *.js *.ts *.html *.css *.java *.cpp *.go);;"
            "Audio (*.mp3 *.wav *.ogg *.m4a *.aac *.flac);;"
            "Video (*.mp4 *.avi *.mov *.mkv *.wmv *.webm);;"
            "Archives (*.zip *.rar *.tar *.gz *.7z)"
        )
        if dlg.exec() == QFileDialog.DialogCode.Accepted:
            files = dlg.selectedFiles()
            if files:
                self._set_file(files[0])

        if parent_win and hasattr(parent_win, "_hud_expanded") and parent_win._hud_expanded:
            def _restore_expanded():
                if parent_win._hud_expanded and not parent_win.isMaximized() and not parent_win.isFullScreen():
                    parent_win.clearMask()
                    parent_win.setMaximumSize(16777215, 16777215)
                    parent_win.setMinimumSize(700, 480)
                    parent_win.resize(820, 540)
            _restore_expanded()
            QTimer.singleShot(30, _restore_expanded)
            QTimer.singleShot(100, _restore_expanded)
            QTimer.singleShot(250, _restore_expanded)

    def _set_file(self, path: str):
        self._current_file = path
        self._canvas.update()
        self.file_selected.emit(path)


class _DropCanvas(QWidget):
    def __init__(self, zone: FileDropZone):
        super().__init__(zone)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")
        self._z = zone

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        z    = self._z
        W, H = self.width(), self.height()
        pad  = 6
        rect = QRectF(pad, pad, W - pad * 2, H - pad * 2)

        if z._drag_over:
            bg_col = QColor(0, 212, 255, 30)
        elif z._hovering:
            bg_col = QColor(0, 212, 255, 18)
        else:
            bg_col = QColor(0, 15, 30, 20)

        p.setBrush(QBrush(bg_col))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, 6, 6)

        if z._current_file:   border_col = qcol(C.GREEN, 200)
        elif z._drag_over:    border_col = qcol(C.PRI, 230)
        elif z._hovering:     border_col = qcol(C.BORDER_B, 200)
        else:                 border_col = QColor(0, 212, 255, 60)

        pen = QPen(border_col, 1.5, Qt.PenStyle.DashLine)
        pen.setDashOffset(z._dash_offset)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 6, 6)

        if z._current_file:   self._paint_file(p, W, H)
        elif z._drag_over:    self._paint_drag_over(p, W, H)
        else:                 self._paint_idle(p, W, H, z._hovering)

    def _paint_idle(self, p, W, H, hover):
        cx, cy = W / 2, H / 2
        col = qcol(C.PRI_DIM if not hover else C.PRI)
        p.setPen(QPen(col, 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(cx, cy - 14), QPointF(cx, cy + 4))
        p.drawLine(QPointF(cx - 8, cy - 6), QPointF(cx, cy - 14))
        p.drawLine(QPointF(cx + 8, cy - 6), QPointF(cx, cy - 14))
        p.drawLine(QPointF(cx - 14, cy + 4), QPointF(cx + 14, cy + 4))
        p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.WHITE if hover else C.PRI), 1))
        p.drawText(QRectF(0, cy + 6, W, 16), Qt.AlignmentFlag.AlignCenter,
                   "Drop file here  or  Click to Browse")
        p.setFont(QFont("Courier New", 7))
        p.setPen(QPen(qcol("#7ec7d8"), 1))
        p.drawText(QRectF(0, cy + 24, W, 14), Qt.AlignmentFlag.AlignCenter,
                   "Images · Video · Audio · PDF · Docs · Code · Data")

    def _paint_drag_over(self, p, W, H):
        cx, cy = W / 2, H / 2
        p.setFont(QFont("Courier New", 20))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(0, cy - 24, W, 32), Qt.AlignmentFlag.AlignCenter, "⬇")
        p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(0, cy + 12, W, 16), Qt.AlignmentFlag.AlignCenter, "Release to load")

    def _paint_file(self, p, W, H):
        path = Path(self._z._current_file)
        cat  = _file_category(path)
        icon, icon_col = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size_str = _fmt_size(path.stat().st_size)
        ext_str  = path.suffix.upper().lstrip(".") or "FILE"

        block_x, block_w = 10, 60
        p.setFont(QFont("Segoe UI Emoji", 22) if _OS == "Windows" else QFont("Arial", 22))
        p.setPen(QPen(qcol(icon_col), 1))
        p.drawText(QRectF(block_x, 0, block_w, H), Qt.AlignmentFlag.AlignCenter, icon)

        tx = block_x + block_w + 6
        tw = W - tx - 38

        p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.WHITE), 1))
        name = path.name if len(path.name) <= 34 else path.name[:31] + "..."
        p.drawText(QRectF(tx, H * 0.18, tw, 16),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

        p.setFont(QFont("Courier New", 7))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(tx, H * 0.18 + 18, tw, 14),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"{ext_str}  ·  {size_str}")

        p.setFont(QFont("Courier New", 6))
        p.setPen(QPen(qcol("#1e5c6a"), 1))
        par = str(path.parent)
        if len(par) > 42: par = "…" + par[-41:]
        p.drawText(QRectF(tx, H * 0.18 + 34, tw, 12),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, par)

        p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.RED, 180), 1))
        p.drawText(QRectF(W - 34, 0, 28, H), Qt.AlignmentFlag.AlignCenter, "✕")

    def mousePressEvent(self, e):
        z = self._z
        if z._current_file and e.pos().x() > self.width() - 34:
            z.clear_file()
        else:
            z.mousePressEvent(e)


class SetupOverlay(QWidget):
    done = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            SetupOverlay {{
                background: rgba(0, 6, 10, 245);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)

        detected = {"darwin": "mac", "windows": "windows"}.get(
            _OS.lower(), "linux"
        )
        self._sel_os = detected

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 22, 30, 22)
        layout.setSpacing(8)

        def _lbl(txt, font_size=9, bold=False, color=C.PRI,
                 align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont("Courier New", font_size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        layout.addWidget(_lbl("◈  INITIALISATION REQUIRED", 13, True))
        layout.addWidget(_lbl("Configure O.R.I.O.N before first boot.", 9, color=C.PRI_DIM))
        layout.addSpacing(6)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep)
        layout.addSpacing(4)

        layout.addWidget(_lbl("GEMINI API KEY", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("AIza…")
        self._key_input.setFont(QFont("Courier New", 10))
        self._key_input.setFixedHeight(32)
        self._key_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        layout.addWidget(self._key_input)
        layout.addSpacing(8)

        layout.addWidget(_lbl("OPENROUTER API KEY", 8, color=C.TEXT_DIM,
                       align=Qt.AlignmentFlag.AlignLeft))
        self._or_input = QLineEdit()
        self._or_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._or_input.setPlaceholderText("sk-or-…")
        self._or_input.setFont(QFont("Courier New", 10))
        self._or_input.setFixedHeight(32)
        self._or_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.ACC2}; }}
        """)
        layout.addWidget(self._or_input)

        layout.addSpacing(12)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep2)
        layout.addSpacing(4)

        layout.addWidget(_lbl("OPERATING SYSTEM", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))
        det_name = {"windows": "Windows", "mac": "macOS", "linux": "Linux"}[detected]
        layout.addWidget(_lbl(f"Auto-detected: {det_name}", 8, color=C.ACC2,
                               align=Qt.AlignmentFlag.AlignLeft))

        os_row = QHBoxLayout(); os_row.setSpacing(6)
        self._os_btns: dict[str, QPushButton] = {}
        for key, label in [("windows","⊞  Windows"),("mac","  macOS"),("linux","🐧  Linux")]:
            btn = QPushButton(label)
            btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._sel(k))
            os_row.addWidget(btn)
            self._os_btns[key] = btn
        layout.addLayout(os_row)
        self._sel(detected)
        layout.addSpacing(12)

        init_btn = QPushButton("▸  INITIALISE SYSTEMS")
        init_btn.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        init_btn.setFixedHeight(36)
        init_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        init_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO}; border: 1px solid {C.PRI};
            }}
        """)
        init_btn.clicked.connect(self._submit)
        layout.addWidget(init_btn)

    def _sel(self, key: str):
        self._sel_os = key
        pal = {"windows":(C.PRI,"#001a22"),"mac":(C.ACC2,"#1a1400"),"linux":(C.GREEN,"#001a0d")}
        for k, btn in self._os_btns.items():
            if k == key:
                fg, bg = pal[k]
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {fg}; color: {bg};
                        border: none; border-radius: 3px; font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #000d12; color: {C.TEXT_DIM};
                        border: 1px solid {C.BORDER}; border-radius: 3px;
                    }}
                    QPushButton:hover {{ color: {C.TEXT}; border: 1px solid {C.BORDER_B}; }}
                """)

    def _submit(self):
        key = self._key_input.text().strip()
        or_key = self._or_input.text().strip()
        if not key:
            self._key_input.setStyleSheet(
                self._key_input.styleSheet() +
                f" QLineEdit {{ border: 1px solid {C.RED}; }}"
            )
            return
        if not or_key:
            self._or_input.setStyleSheet(
                self._or_input.styleSheet() +
                f" QLineEdit {{ border: 1px solid {C.RED}; }}"
            )
            return
        self.done.emit(key, or_key, self._sel_os)


class MainWindow(QMainWindow):
    _log_sig   = pyqtSignal(str)
    _state_sig = pyqtSignal(str)
    _vitals_sig = pyqtSignal(dict)
    wake_signal = pyqtSignal()

    def __init__(self, face_path: str = ""):
        super().__init__()
        setup_dark_app_theme(QApplication.instance())
        self.setWindowTitle("O.R.I.O.N — MARK I")

        # Frameless, stay-on-top, and translucent for Pop!_OS COSMIC / Wayland
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setStyleSheet("QMainWindow { background: transparent; border: none; }")

        self.on_text_command = None
        self._muted = False
        self._current_file: str | None = None
        self._hud_expanded = False

        central = QWidget(self)
        central.setObjectName("CentralWidget")
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        central.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        central.setStyleSheet("QWidget#CentralWidget { background: transparent; border: none; }")
        self.setCentralWidget(central)

        self._root_layout = QVBoxLayout(central)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # 1. Glass Header (_ [] X, Clock, Title)
        self._header = GlassHeaderWidget(self)
        self._header.minimize_clicked.connect(lambda: self.set_hud_expanded(False))
        self._header.maximize_clicked.connect(self._toggle_maximize)
        self._header.close_clicked.connect(self.close)
        self._root_layout.addWidget(self._header)

        # 2. Main Body Container
        self._body_layout = QHBoxLayout()
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(8)

        # 2a. Visage Container (houses OrionParticleCanvas and VitalsToastOverlay)
        self._visage_container = QWidget()
        self._visage_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._visage_container.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._visage_container.setStyleSheet("background: transparent; border: none;")
        self._visage_container.setMinimumSize(260, 260)
        v_layout = QVBoxLayout(self._visage_container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(6)

        self.hud = OrionParticleCanvas(self._visage_container)
        self.hud.setMinimumSize(260, 260)
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.hud.visageClicked.connect(self._on_visage_clicked)
        v_layout.addWidget(self.hud, stretch=1)

        self._vitals_toast = VitalsToastOverlay(self._visage_container)
        v_layout.addWidget(self._vitals_toast, alignment=Qt.AlignmentFlag.AlignCenter)

        self._body_layout.addWidget(self._visage_container, stretch=1)

        # 2b. Right Panel (translucent glassmorphic HUD controls)
        self._right_panel = self._build_right_panel()
        self._body_layout.addWidget(self._right_panel, stretch=0)

        self._root_layout.addLayout(self._body_layout, stretch=1)

        # Clock timer for header
        self._clock_tmr = QTimer(self)
        self._clock_tmr.timeout.connect(self._header.tick)
        self._clock_tmr.start(1000)
        self._header.tick()

        self._log_sig.connect(self._log.append_log)
        self._state_sig.connect(self._apply_state)
        self._vitals_sig.connect(self._vitals_toast.display)
        self.wake_signal.connect(self.bring_to_front)

        self._overlay: SetupOverlay | None = None
        self._ready = self._check_config()
        if not self._ready:
            self._show_setup()

        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)
        sc_full = QShortcut(QKeySequence("F11"), self)
        sc_full.activated.connect(self._toggle_fullscreen)
        sc_esc = QShortcut(QKeySequence("Escape"), self)
        sc_esc.activated.connect(self._handle_escape)

        self._pending_collapse_to_orb = False
        self._maximized_from_compact = False
        self._drag_start_pos = None

        # Default state: minimalist compact floating orb
        self.set_hud_expanded(False)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width() - 300) // 2,
            (screen.height() - 300) // 2,
        )

    def _on_visage_clicked(self):
        if not self._hud_expanded:
            self.set_hud_expanded(True)
        else:
            # When already expanded or full screen, clicking on Orion activates microphone / un-mutes
            # or focuses command input rather than collapsing the window into a broken state
            if getattr(self, '_muted', False):
                self._toggle_mute()
            elif hasattr(self, '_input'):
                self._input.setFocus()

    def set_hud_expanded(self, expanded: bool):
        self._hud_expanded = expanded
        if expanded:
            self._pending_collapse_to_orb = False
            self._body_layout.setAlignment(self._visage_container, Qt.AlignmentFlag.AlignCenter)
            cw = self.centralWidget()
            if cw:
                cw.setMinimumSize(820, 540)
                cw.setMaximumSize(16777215, 16777215)
            self._visage_container.setMinimumSize(260, 260)
            self._visage_container.setMaximumSize(16777215, 16777215)
            self.hud.setMinimumSize(260, 260)
            self.hud.setMaximumSize(16777215, 16777215)
            self.setMinimumSize(820, 540)
            self.setMaximumSize(16777215, 16777215)
            self._root_layout.setContentsMargins(8, 6, 8, 8)
            self._root_layout.setSpacing(6)
            self._body_layout.setContentsMargins(0, 0, 0, 0)
            self._body_layout.setSpacing(8)
            self._header.show()
            self._right_panel.show()
            if not self.isMaximized() and not self.isFullScreen():
                self.resize(820, 540)
            QTimer.singleShot(60, lambda: self.setMinimumSize(700, 480) if self._hud_expanded else None)
        else:
            was_max = self.isMaximized() or self.isFullScreen()
            if was_max:
                self._pending_collapse_to_orb = True
                self.showNormal()
            self._apply_compact_orb_geometry()
            # Under Wayland, force surface unmap/remap so cosmic-comp destroys
            # the cached 820x540 surface and instantiates a pristine 300x300 surface.
            if QGuiApplication.platformName() == "wayland" and self.isVisible():
                self.hide()
                self._apply_compact_orb_geometry()
                self.show()
            QTimer.singleShot(20, self._apply_compact_orb_geometry)
            QTimer.singleShot(80, self._apply_compact_orb_geometry)

    def _apply_compact_orb_geometry(self):
        self._pending_collapse_to_orb = False
        self._header.hide()
        self._right_panel.hide()
        self._vitals_toast.hide()
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(0)
        self._body_layout.setAlignment(self._visage_container, Qt.AlignmentFlag.AlignCenter)
        cw = self.centralWidget()
        if cw:
            cw.setFixedSize(300, 300)
        self._visage_container.setFixedSize(300, 300)
        self.hud.setFixedSize(300, 300)
        self.setFixedSize(300, 300)
        self.resize(300, 300)
        wh = self.windowHandle()
        if wh:
            wh.resize(QSize(300, 300))

    def toggle_hud_state(self):
        self.set_hud_expanded(not self._hud_expanded)

    def show_vitals_toast(self, data: dict):
        self._vitals_sig.emit(data)
        summary = data.get("speech_summary", "")
        if summary:
            self._log.append_log(f"SYS: {summary}")

    def _toggle_maximize(self):
        if self.isMaximized() or self.isFullScreen():
            if getattr(self, '_maximized_from_compact', False) or not self._hud_expanded:
                self._maximized_from_compact = False
                self.set_hud_expanded(False)
            else:
                self.setMinimumSize(820, 540)
                self.setMaximumSize(16777215, 16777215)
                self.showNormal()
                self.resize(820, 540)
                QTimer.singleShot(60, lambda: self.setMinimumSize(700, 480) if self._hud_expanded else None)
        else:
            if not self._hud_expanded:
                self._maximized_from_compact = True
                self.set_hud_expanded(True)
            else:
                self._maximized_from_compact = False
            self.showMaximized()

    def _toggle_fullscreen(self):
        if self.isFullScreen() or self.isMaximized():
            if getattr(self, '_maximized_from_compact', False) or not self._hud_expanded:
                self._maximized_from_compact = False
                self.set_hud_expanded(False)
            else:
                self.setMinimumSize(820, 540)
                self.setMaximumSize(16777215, 16777215)
                self.showNormal()
                self.resize(820, 540)
                QTimer.singleShot(60, lambda: self.setMinimumSize(700, 480) if self._hud_expanded else None)
        else:
            if not self._hud_expanded:
                self._maximized_from_compact = True
                self.set_hud_expanded(True)
            else:
                self._maximized_from_compact = False
            self.showFullScreen()

    def _handle_escape(self):
        if self.isFullScreen() or self.isMaximized():
            if getattr(self, '_maximized_from_compact', False) or not self._hud_expanded:
                self._maximized_from_compact = False
                self.set_hud_expanded(False)
            else:
                self.setMinimumSize(820, 540)
                self.setMaximumSize(16777215, 16777215)
                self.showNormal()
                self.resize(820, 540)
                QTimer.singleShot(60, lambda: self.setMinimumSize(700, 480) if self._hud_expanded else None)
        elif self._hud_expanded:
            self.set_hud_expanded(False)

    def mousePressEvent(self, event):
        if not self._hud_expanded and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_win_pos = self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._hud_expanded and getattr(self, '_drag_start_pos', None) is not None:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            if delta.manhattanLength() >= 4:
                if not self.isMaximized() and not self.isFullScreen():
                    wh = self.windowHandle()
                    if wh and QGuiApplication.platformName() == "wayland":
                        wh.startSystemMove()
                        self._drag_start_pos = None
                        return
                    elif QGuiApplication.platformName() != "wayland":
                        self.move(self._drag_win_pos + delta)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self._drag_start_pos = None
        super().leaveEvent(event)

    def closeEvent(self, event):
        """Instantly hides the UI and resets wake-word buffers to prevent pop-up bounces."""
        event.ignore()

        listener = getattr(self, 'listener', None)
        if listener:
            listener.pause_listening()

        orion = getattr(self, 'orion', None)
        if orion and hasattr(orion, 'stop_speaking'):
            orion.stop_speaking()

        self.hide()
        QApplication.sendPostedEvents()

        def _deferred_resume():
            listener = getattr(self, 'listener', None)
            if listener:
                listener.resume_listening()
                print("🐺 [ANUBIS]: Wake-word predictions resumed cleanly.")

        QTimer.singleShot(250, _deferred_resume)
        print("🐺 [ANUBIS]: Window hidden to background.")

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            listener = getattr(self, 'listener', None)
            
            if self.isMinimized():
                print("🐺 [ANUBIS]: Window minimized, wake listener active.")
                if listener:
                    listener.resume_listening()
            else:
                if listener and event.oldState() & Qt.WindowState.WindowMinimized:
                    print("🐺 [ANUBIS]: Window restored from minimized.")
                    listener.pause_listening()

                if not self.isMaximized() and not self.isFullScreen():
                    if getattr(self, '_pending_collapse_to_orb', False) or not self._hud_expanded:
                        self._apply_compact_orb_geometry()
                        if QGuiApplication.platformName() == "wayland" and self.isVisible():
                            if self.size().width() != 300 or self.size().height() != 300:
                                self.hide()
                                self._apply_compact_orb_geometry()
                                self.show()
                        QTimer.singleShot(20, self._apply_compact_orb_geometry)
                        QTimer.singleShot(80, self._apply_compact_orb_geometry)
                    elif self._hud_expanded:
                        self.setMinimumSize(820, 540)
                        self.setMaximumSize(16777215, 16777215)
                        self._header.show()
                        self._right_panel.show()
                        QTimer.singleShot(50, lambda: self.resize(820, 540) if self._hud_expanded and not self.isMaximized() and not self.isFullScreen() else None)
                        QTimer.singleShot(120, lambda: self.setMinimumSize(700, 480) if self._hud_expanded else None)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._hud_expanded and not self.isMaximized() and not self.isFullScreen():
            # Guard against Wayland compositor transient configure events collapsing expanded HUD
            if event.size().width() < 700 or event.size().height() < 480:
                self.setMinimumSize(820, 540)
                self.setMaximumSize(16777215, 16777215)
                QTimer.singleShot(10, lambda: self.resize(820, 540) if self._hud_expanded and not self.isMaximized() and not self.isFullScreen() else None)
        elif not self._hud_expanded and not self.isMaximized() and not self.isFullScreen():
            # Guard against Wayland compositor leaving compact orb expanded to pre-maximize size (e.g. 820x540)
            if (event.size().width() != 300 or event.size().height() != 300) and not getattr(self, '_in_compact_fix', False):
                self._in_compact_fix = True
                try:
                    self._apply_compact_orb_geometry()
                    if QGuiApplication.platformName() == "wayland" and self.isVisible():
                        self.hide()
                        self._apply_compact_orb_geometry()
                        self.show()
                    QTimer.singleShot(10, self._apply_compact_orb_geometry)
                    QTimer.singleShot(50, self._apply_compact_orb_geometry)
                finally:
                    self._in_compact_fix = False
        if self._overlay and self._overlay.isVisible():
            ow, oh = 460, 390
            cw = self.centralWidget()
            self._overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )

    def _build_right_panel(self) -> QWidget:
        w = QFrame()
        w.setObjectName("GlassPanel")
        w.setFixedWidth(_RIGHT_W)
        w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        w.setStyleSheet("""
            QFrame#GlassPanel {
                background-color: rgba(2, 10, 18, 0.40);
                border: 1px solid rgba(0, 212, 255, 0.28);
                border-radius: 8px;
            }
            QLabel {
                color: #5ab8cc;
                background: transparent;
            }
        """)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        def _sec(txt):
            l = QLabel(f"▸ {txt}")
            l.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            l.setStyleSheet("color: #59d4e6; background: transparent;")
            return l

        lay.addWidget(_sec("ACTIVITY LOG"))
        self._log = LogWidget()
        lay.addWidget(self._log, stretch=1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(0, 212, 255, 0.2); margin: 2px 0;")
        lay.addWidget(sep)

        lay.addWidget(_sec("FILE UPLOAD"))
        self._drop_zone = FileDropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        lay.addWidget(self._drop_zone)

        self._file_hint = QLabel("No file loaded — drop or click above to upload")
        self._file_hint.setFont(QFont("Courier New", 7))
        self._file_hint.setStyleSheet("color: #7ec7d8; background: transparent;")
        self._file_hint.setWordWrap(True)
        lay.addWidget(self._file_hint)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: rgba(0, 212, 255, 0.2); margin: 2px 0;")
        lay.addWidget(sep2)

        lay.addWidget(_sec("COMMAND INPUT"))
        lay.addLayout(self._build_input_row())

        self._mute_btn = QPushButton("🎙  MICROPHONE ACTIVE")
        self._mute_btn.setFixedHeight(30)
        self._mute_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mute_btn.clicked.connect(self._toggle_mute)
        self._style_mute_btn()
        lay.addWidget(self._mute_btn)

        fs_btn = QPushButton("⛶  FULLSCREEN  [F11]")
        fs_btn.setFixedHeight(26)
        fs_btn.setFont(QFont("Courier New", 7))
        fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fs_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 212, 255, 0.10);
                color: #5ab8cc;
                border: 1px solid rgba(0, 212, 255, 0.25);
                border-radius: 4px;
            }
            QPushButton:hover {
                color: #00d4ff;
                border: 1px solid #00d4ff;
                background: rgba(0, 212, 255, 0.22);
            }
        """)
        fs_btn.clicked.connect(self._toggle_fullscreen)
        lay.addWidget(fs_btn)

        return w

    def _build_input_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(5)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command or question…")
        self._input.setFont(QFont("Courier New", 9))
        self._input.setFixedHeight(30)
        self._input.setStyleSheet("""
            QLineEdit {
                background: rgba(0, 20, 35, 0.25);
                color: #d8f8ff;
                border: 1px solid rgba(0, 212, 255, 0.25);
                border-radius: 4px;
                padding: 3px 8px;
            }
            QLineEdit:focus {
                border: 1px solid #00d4ff;
                background: rgba(0, 35, 60, 0.40);
            }
        """)
        self._input.returnPressed.connect(self._send)
        row.addWidget(self._input)

        send = QPushButton("▶")
        send.setFixedSize(30, 30)
        send.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setStyleSheet("""
            QPushButton {
                background: rgba(0, 212, 255, 0.12);
                color: #00d4ff;
                border: 1px solid rgba(0, 212, 255, 0.30);
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(0, 212, 255, 0.28);
                border: 1px solid #00d4ff;
                color: #ffffff;
            }
        """)
        send.clicked.connect(self._send)
        row.addWidget(send)
        return row

    def _on_file_selected(self, path: str):
        self._current_file = path
        p    = Path(path)
        cat  = _file_category(p)
        icon, _ = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size = _fmt_size(p.stat().st_size)
        self._file_hint.setText(f"{icon}  {p.name}  ·  {size}  ·  Tell O.R.I.O.N what to do with it")
        self._log.append_log(f"FILE: {p.name} ({size}) loaded")
        if self.on_text_command:
            msg = (
                f"[FILE_UPLOADED] path={path} | name={p.name} | "
                f"type={p.suffix.lstrip('.')} | size={size} | "
                f"Briefly tell the user you can see the file '{p.name}' "
                f"({size}) has been uploaded and ask what they'd like to do with it."
            )
            threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        self._style_mute_btn()
        if self._muted:
            self._apply_state("MUTED")
            self._log.append_log("SYS: Microphone muted.")
        else:
            self._apply_state("LISTENING")
            self._log.append_log("SYS: Microphone active.")

    def _style_mute_btn(self):
        if self._muted:
            self._mute_btn.setText("🔇  MICROPHONE MUTED")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255, 51, 102, 0.10);
                    color: {C.MUTED_C};
                    border: 1px solid rgba(255, 51, 102, 0.45);
                    border-radius: 4px;
                    padding: 5px;
                    font-family: 'Courier New', monospace;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: rgba(255, 51, 102, 0.22);
                    border: 1px solid {C.MUTED_C};
                }}
            """)
        else:
            self._mute_btn.setText("🎙  MICROPHONE ACTIVE")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(0, 255, 136, 0.08);
                    color: {C.GREEN};
                    border: 1px solid rgba(0, 255, 136, 0.45);
                    border-radius: 4px;
                    padding: 5px;
                    font-family: 'Courier New', monospace;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: rgba(0, 255, 136, 0.20);
                    border: 1px solid {C.GREEN};
                }}
            """)

    def _send(self):
        txt = self._input.text().strip()
        if not txt: return
        self._input.clear()
        self._log.append_log(f"You: {txt}")
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(txt,), daemon=True).start()

    def _apply_state(self, state: str):
        self.hud.state    = state
        self.hud.speaking = (state == "SPEAKING")

    def _check_config(self) -> bool:
        if not API_FILE.exists(): return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            return (bool(d.get("gemini_api_key")) and
                    bool(d.get("groq_api_key")) and
                    bool(d.get("os_system")))
        except Exception:
            return False

    def _show_setup(self):
        ov = SetupOverlay(self.centralWidget())
        cw = self.centralWidget()
        ow, oh = 460, 430
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.done.connect(self._on_setup_done)
        ov.show()
        self._overlay = ov

    def bring_to_front(self):
        """Pops UI on screen in COMPACT_ORB mode and pauses wake-word predictions."""
        listener = getattr(self, 'listener', None)
        if listener:
            listener.pause_listening()
            print("🐺 [ANUBIS]: Wake-word predictions paused.")

        self.set_hud_expanded(False)
        self.show()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(30, self._apply_compact_orb_geometry)
        print("🐺 [ANUBIS]: Window popped up on screen in COMPACT_ORB.")

    def _on_setup_done(self, key: str, or_key: str, os_name: str):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_FILE.write_text(
            json.dumps({
                "gemini_api_key":    key,
                "openrouter_api_key": or_key,
                "os_system":         os_name,
            }, indent=4),
            encoding="utf-8",
        )
        self._ready = True
        if self._overlay:
            self._overlay.hide()
            self._overlay = None
        self._apply_state("LISTENING")
        self._log.append_log(f"SYS: Initialised. OS={os_name.upper()}. O.R.I.O.N online.")

class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app
    def mainloop(self):
        self._app.exec()
    def protocol(self, *_):
        pass


class JarvisUI:
    def __init__(self, face_path: str, size=None, minimized: bool = False):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)
        setup_dark_app_theme(self._app)
        self._win = MainWindow(face_path)
        if minimized:
            self._win.hide()
        else:
            self._win.show()
        self.root = _RootShim(self._app)

    @property
    def listener(self):
        return getattr(self._win, "listener", None)

    @listener.setter
    def listener(self, l):
        self._win.listener = l

    @property
    def wake_signal(self):
        return self._win.wake_signal

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return self._win._drop_zone.current_file()

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    def write_log(self, text: str):
        self._win._log_sig.emit(text)

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    def show_vitals_toast(self, data: dict):
        self._win.show_vitals_toast(data)

    @property
    def wake_signal(self):
        return self._win.wake_signal

    def bring_to_front(self):
        self._win.wake_signal.emit()

    def toggle_hud_state(self):
        self._win.toggle_hud_state()

    def set_hud_expanded(self, expanded: bool):
        self._win.set_hud_expanded(expanded)
