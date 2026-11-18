"""
Unit tests for Orion 3D Visage Particle Engine.
"""

import os
import sys
import pytest
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QMouseEvent

# Ensure Anubis is on path
ANUBIS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ANUBIS_DIR not in sys.path:
    sys.path.insert(0, ANUBIS_DIR)

from orion_visage import (
    generate_orion_point_cloud,
    OrionParticleCanvas,
    _GLVisageWidget,
    _SoftwareVisageWidget,
)

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_point_cloud_generation():
    cloud = generate_orion_point_cloud()
    assert isinstance(cloud, np.ndarray)
    assert cloud.ndim == 2
    assert cloud.shape[1] == 6
    assert cloud.shape[0] > 3000  # Expect ~3,400 particles (visage + living corona)

    visage = cloud[cloud[:, 3] <= 1.0]
    corona = cloud[cloud[:, 3] >= 1.5]

    x0 = visage[:, 0]
    y0 = visage[:, 1]
    z0 = visage[:, 2]
    role = visage[:, 3]

    # Bounds check visage normalized space
    assert np.min(x0) >= -0.75
    assert np.max(x0) <= 0.75
    assert np.min(y0) >= -1.05
    assert np.max(y0) <= 1.05

    # Visage Z curvature is in front of origin
    assert np.all(z0 > 0.0)

    # Visage roles must be 0.0 (interior) or 1.0 (perimeter)
    assert set(np.unique(role)).issubset({0.0, 1.0})
    assert np.sum(role == 1.0) > 300
    assert np.sum(role == 0.0) > 1000

    # Living Corona extends behind Orion (Z < 0)
    assert len(corona) >= 800
    assert np.min(corona[:, 2]) < -0.5




def test_canvas_lifecycle_and_api(qapp):
    canvas = OrionParticleCanvas()
    assert canvas.state == "INITIALISING"

    canvas.set_state("LISTENING")
    assert canvas.state == "LISTENING"
    assert canvas._renderer.state_code == 1

    canvas.set_speaking(True)
    assert canvas.state == "SPEAKING"
    assert canvas.speaking is True
    assert canvas._renderer.state_code == 2

    canvas.set_speaking(False)
    assert canvas.speaking is False
    assert canvas.state == "IDLE"
    assert canvas._renderer.state_code == 0

    canvas.set_muted(True)
    assert canvas.muted is True
    assert canvas._renderer.state_code == 3

    canvas.set_muted(False)
    assert canvas.muted is False
    assert canvas._renderer.state_code == 0

    canvas.set_audio_level(0.85)
    assert canvas._audio_level == 0.85


def test_software_renderer_fallback(qapp):
    cloud = generate_orion_point_cloud()
    soft = _SoftwareVisageWidget(cloud)
    soft.resize(250, 300)
    assert soft.num_points == len(cloud)


def test_click_signal_emission(qapp):
    canvas = OrionParticleCanvas()
    clicked = []
    canvas.visageClicked.connect(lambda: clicked.append(True))

    # Simulate quick click
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(50, 50),
        QPointF(50, 50),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press_event)

    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(50, 50),
        QPointF(50, 50),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseReleaseEvent(release_event)

    assert len(clicked) == 1


def test_drag_suppresses_click_signal(qapp):
    canvas = OrionParticleCanvas()
    clicked = []
    canvas.visageClicked.connect(lambda: clicked.append(True))

    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(50, 50),
        QPointF(50, 50),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(70, 70),
        QPointF(70, 70),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(70, 70),
        QPointF(70, 70),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    canvas.mousePressEvent(press_event)
    canvas.mouseMoveEvent(move_event)
    assert canvas._is_dragging is True
    canvas.mouseReleaseEvent(release_event)

    # Dragging must NOT trigger visageClicked
    assert len(clicked) == 0


def test_gl_widget_transparency_and_stacking(qapp):
    cloud = generate_orion_point_cloud()
    gl_widget = _GLVisageWidget(cloud)
    assert gl_widget.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) is True
    assert gl_widget.testAttribute(Qt.WidgetAttribute.WA_NoSystemBackground) is True
    assert gl_widget.testAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop) is True
    assert "background: transparent" in gl_widget.styleSheet()


def test_spherical_body_containment():
    cloud = generate_orion_point_cloud()
    body_pts = cloud[cloud[:, 3] >= 1.5]
    radial_distances = np.sqrt(body_pts[:, 0]**2 + body_pts[:, 1]**2 + body_pts[:, 2]**2)
    # Strictly contained within sphere R <= 1.02
    assert np.max(radial_distances) <= 1.02
    # At zoom = 0.78, maximum screen coordinate in NDC is 1.02 * 0.78 = 0.7956 < 1.0
    assert np.max(radial_distances) * 0.78 < 0.85


def test_canvas_mouse_double_click_avoids_duplicate_visage_clicked(qapp):
    canvas = OrionParticleCanvas()
    clicked = []
    canvas.visageClicked.connect(lambda: clicked.append(True))

    pos = QPointF(150.0, 150.0)
    press_event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, pos, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    release_event = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    dbl_click_event = QMouseEvent(QMouseEvent.Type.MouseButtonDblClick, pos, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)

    # 1. First click
    canvas.mousePressEvent(press_event)
    canvas.mouseReleaseEvent(release_event)
    assert len(clicked) == 1

    # 2. Double click immediately following
    canvas.mousePressEvent(press_event)
    canvas.mouseDoubleClickEvent(dbl_click_event)
    assert canvas._is_double_click is True
    canvas.mouseReleaseEvent(release_event)
    # The release after double click must NOT emit a second visageClicked
    assert len(clicked) == 1
    assert canvas._is_double_click is False



