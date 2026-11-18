"""
Unit tests for modernized minimalist Orion UI and glassmorphic HUD state machine.
"""

import os
import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

ANUBIS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ANUBIS_DIR not in sys.path:
    sys.path.insert(0, ANUBIS_DIR)

from ui import MainWindow, JarvisUI, VitalsToastOverlay, GlassHeaderWidget
from orion_visage import OrionParticleCanvas


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_mainwindow_compact_by_default(qapp):
    win = MainWindow()
    # By default, Orion must start in COMPACT_ORB mode
    assert win._hud_expanded is False
    assert win._header.isHidden() is True
    assert win._right_panel.isHidden() is True
    assert win.width() <= 360
    assert win.height() <= 420
    assert isinstance(win.hud, OrionParticleCanvas)


def test_toggle_hud_state_expansion_and_collapse(qapp):
    win = MainWindow()
    win.show()
    assert win._hud_expanded is False

    # Expand on click
    win.toggle_hud_state()
    assert win._hud_expanded is True
    assert win._header.isHidden() is False
    assert win._right_panel.isHidden() is False
    assert win._header.isVisible() is True
    assert win._right_panel.isVisible() is True
    assert win.width() >= 700
    assert win.height() >= 480

    # Collapse on click
    win.toggle_hud_state()
    assert win._hud_expanded is False
    assert win._header.isHidden() is True
    assert win._right_panel.isHidden() is True
    assert win.width() <= 360
    assert win.height() <= 420


def test_bring_to_front_resets_to_compact(qapp):
    win = MainWindow()
    win.show()
    win.set_hud_expanded(True)
    assert win._hud_expanded is True

    # When wake-word triggers bring_to_front, HUD must fold into compact visage
    win.bring_to_front()
    assert win._hud_expanded is False
    assert win._header.isHidden() is True
    assert win._right_panel.isHidden() is True


def test_vitals_toast_display(qapp):
    win = MainWindow()
    win.show()
    data = {
        "speech_summary": "All systems nominal. CPU is at 15 percent, memory at 50 percent.",
        "cpu": {"percent": 15.2, "temp_c": 55.0},
        "memory": {"percent": 50.0},
        "gpu": {"available": True, "util_pct": 22.0, "temp_c": 48.0},
    }
    win.show_vitals_toast(data)
    assert win._vitals_toast.isHidden() is False
    assert win._vitals_toast.isVisible() is True
    assert "15%" in win._vitals_toast._cpu_lbl.text()
    assert "50%" in win._vitals_toast._mem_lbl.text()
    assert "22%" in win._vitals_toast._gpu_lbl.text()


def test_jarvis_ui_facade(qapp):
    jui = JarvisUI(face_path="", minimized=True)
    assert hasattr(jui, "show_vitals_toast")
    assert hasattr(jui, "bring_to_front")
    assert hasattr(jui, "toggle_hud_state")
    assert hasattr(jui, "set_hud_expanded")

    jui.set_hud_expanded(True)
    assert jui._win._hud_expanded is True
    jui.set_hud_expanded(False)
    assert jui._win._hud_expanded is False


def test_maximize_and_minimize_cycles_cleanly(qapp):
    win = MainWindow()
    win.show()
    win.set_hud_expanded(True)
    assert win.width() >= 700
    assert win._right_panel.isVisible() is True

    # Maximize window
    win._toggle_maximize()
    assert win.isMaximized() is True

    # Restore window
    win._toggle_maximize()
    assert win.isMaximized() is False
    assert win.width() >= 700
    assert win._right_panel.width() == 340
    assert win._visage_container.width() >= 240

    # Minimize window
    win.showMinimized()
    assert win.isMinimized() is True

    # Restore from minimized
    win.showNormal()
    assert win.isMinimized() is False
    assert win._hud_expanded is True
    assert win.width() >= 700
    assert win._right_panel.isVisible() is True

    # Collapse to compact
    win.set_hud_expanded(False)
    assert win._hud_expanded is False
    assert win._right_panel.isHidden() is True
    assert win.width() <= 360
    assert win.height() <= 420
    win.close()


def test_header_minimize_collapses_to_compact_orb(qapp):
    win = MainWindow()
    win.show()
    win.set_hud_expanded(True)
    assert win._hud_expanded is True
    assert win._header.isVisible() is True
    assert win._right_panel.isVisible() is True

    # Clicking header minimize button collapses HUD to compact orb rather than taskbar minimize
    win._header.minimize_clicked.emit()
    assert win._hud_expanded is False
    assert win._header.isHidden() is True
    assert win._right_panel.isHidden() is True
    assert win.width() <= 360
    assert win.height() <= 360
    win.close()


def test_dark_palette_contrast_applied(qapp):
    from ui import setup_dark_app_theme
    from PyQt6.QtGui import QPalette

    setup_dark_app_theme(qapp)
    pal = qapp.palette()

    # Verify high-contrast dark theme colors
    text_color = pal.color(QPalette.ColorRole.Text)
    window_text = pal.color(QPalette.ColorRole.WindowText)
    base_color = pal.color(QPalette.ColorRole.Base)
    window_color = pal.color(QPalette.ColorRole.Window)

    # Base and Window should be dark midnight navy (brightness < 60)
    assert base_color.lightness() < 60
    assert window_color.lightness() < 60

    # Text and WindowText must be luminous and bright (brightness > 200)
    assert text_color.lightness() > 200
    assert window_text.lightness() > 200


def test_visage_click_expands_when_compact_and_does_not_collapse_when_expanded(qapp):
    win = MainWindow()
    win.show()
    assert win._hud_expanded is False

    # 1. Click visage in compact orb mode -> expands to HUD
    win.hud.visageClicked.emit()
    assert win._hud_expanded is True
    assert win._header.isVisible() is True
    assert win._right_panel.isVisible() is True

    # 2. Click visage in expanded mode -> does NOT collapse the window
    win.hud.visageClicked.emit()
    assert win._hud_expanded is True
    assert win._header.isVisible() is True
    assert win._right_panel.isVisible() is True

    # 3. Fullscreen / maximize -> click visage still does NOT collapse
    win._toggle_maximize()
    assert win.isMaximized() is True
    win.hud.visageClicked.emit()
    assert win._hud_expanded is True
    assert win.isMaximized() is True
    win.close()


def test_collapse_from_maximized_or_fullscreen_restores_compact_geometry(qapp):
    win = MainWindow()
    win.show()
    win.set_hud_expanded(True)
    win.showMaximized()
    assert win.isMaximized() is True

    # Calling set_hud_expanded(False) from maximized/fullscreen state
    win.set_hud_expanded(False)

    # Either immediately via changeEvent or on compositor callback, compact geometry is restored
    if win._pending_collapse_to_orb:
        win._apply_compact_orb_geometry()

    assert win._hud_expanded is False
    assert win._pending_collapse_to_orb is False
    assert win._header.isHidden() is True
    assert win._right_panel.isHidden() is True
    assert win.width() == 300
    assert win.height() == 300
    win.close()


def test_escape_key_handler(qapp):
    win = MainWindow()
    win.show()
    win.set_hud_expanded(True)
    win.showFullScreen()
    assert win.isFullScreen() is True

    # Escape while fullscreen -> restores normal expanded HUD
    win._handle_escape()
    assert win.isFullScreen() is False
    assert win._hud_expanded is True

    # Escape while normal expanded HUD -> collapses to compact orb
    win._handle_escape()
    assert win._hud_expanded is False
    assert win.width() <= 360
    assert win.height() <= 360
    win.close()


def test_hud_widgets_transparency(qapp):
    win = MainWindow()
    win.show()
    win.set_hud_expanded(True)

    # Activity Log transparency
    assert win._log.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) is True
    assert win._log.viewport().testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) is True
    assert "rgba(" in win._log.styleSheet() or "transparent" in win._log.styleSheet()

    # File Drop Zone & Drop Canvas transparency
    assert win._drop_zone.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) is True
    assert win._drop_zone._canvas.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) is True

    # Microphone button transparency
    win._muted = False
    win._style_mute_btn()
    assert "rgba(0, 255, 136, 0.08)" in win._mute_btn.styleSheet()
    win._muted = True
    win._style_mute_btn()
    assert "rgba(255, 51, 102, 0.10)" in win._mute_btn.styleSheet()

    # Right glass panel transparency
    assert win._right_panel.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) is True
    assert "rgba(2, 10, 18, 0.40)" in win._right_panel.styleSheet()

    win.close()


def test_toggle_maximize_from_fullscreen_restores_cleanly(qapp):
    win = MainWindow()
    win.show()
    win.set_hud_expanded(True)
    win.showFullScreen()
    assert win.isFullScreen() is True

    # Double click or toggle maximize while fullscreen must restore to normal rather than erroring
    win._toggle_maximize()
    assert win.isFullScreen() is False
    assert win._hud_expanded is True
    assert win.width() >= 700
    win.close()




