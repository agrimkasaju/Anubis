"""
O.R.I.O.N 3D Visage Particle Engine.
Transforms Orion's cybernetic logo paths into a responsive 3D particle entity.
Dual-backend support: QOpenGLWidget (GLSL 330, premultiplied alpha) with vectorized QPainter fallback.
"""

from __future__ import annotations
import math
import os
import re
import sys
import time
import numpy as np

from PyQt6.QtCore import Qt, QPointF, QTimer, pyqtSignal, QEvent
from PyQt6.QtGui import (
    QPainter,
    QPainterPath,
    QPolygonF,
    QColor,
    QRadialGradient,
    QPixmap,
    QGuiApplication,
)
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtOpenGL import (
    QOpenGLShaderProgram,
    QOpenGLShader,
    QOpenGLBuffer,
    QOpenGLVertexArrayObject,
)

# Symmetrical SVG contours from Anubis/frontend/src/components/OrionLogo.tsx (ViewBox: 0 0 100 140)
ORION_PATH_LEFT = (
    "M 36.71,10.00 L 35.93,10.57 L 35.25,11.26 L 34.61,11.97 L 33.92,12.65 L 33.26,13.32 "
    "L 32.69,14.04 L 32.16,14.78 L 31.47,15.46 L 30.75,16.12 L 30.09,16.80 L 29.43,17.50 "
    "L 28.71,18.11 L 27.95,18.57 L 27.29,19.29 L 26.59,19.92 L 25.86,20.47 L 25.12,20.99 "
    "L 24.39,21.55 L 23.69,22.18 L 23.01,22.84 L 22.33,23.52 L 21.66,24.21 L 20.98,24.89 "
    "L 20.30,25.57 L 19.62,26.24 L 18.94,26.91 L 18.26,27.59 L 17.58,28.27 L 16.93,28.96 "
    "L 16.32,29.67 L 15.78,30.40 L 15.25,31.14 L 14.73,31.88 L 14.25,32.64 L 13.73,33.39 "
    "L 13.25,34.14 L 12.82,34.92 L 12.43,35.72 L 12.12,36.55 L 11.77,37.37 L 11.46,38.20 "
    "L 11.14,39.02 L 11.04,39.94 L 10.74,40.78 L 10.55,41.65 L 10.39,42.55 L 10.29,43.46 "
    "L 10.04,44.33 L 10.10,45.28 L 10.03,46.27 L 10.11,47.19 L 10.35,48.05 L 10.44,48.97 "
    "L 10.39,49.95 L 10.48,50.87 L 10.75,51.72 L 10.94,52.60 L 11.23,53.44 L 11.61,54.24 "
    "L 11.90,55.08 L 12.25,55.89 L 12.68,56.67 L 13.04,57.48 L 13.54,58.23 L 14.00,59.00 "
    "L 14.43,59.78 L 14.94,60.53 L 15.51,61.25 L 16.03,61.99 L 16.60,62.72 L 17.14,63.45 "
    "L 17.72,64.17 L 18.41,64.84 L 18.89,65.60 L 19.51,66.31 L 20.24,66.96 L 20.75,67.71 "
    "L 21.32,68.43 L 21.98,69.11 L 22.68,69.79 L 23.36,70.46 L 24.03,71.14 L 24.71,71.82 "
    "L 25.36,72.51 L 25.84,73.27 L 26.48,73.96 L 27.14,74.65 L 27.64,75.40 L 28.18,76.13 "
    "L 28.76,76.85 L 29.30,77.59 L 29.84,78.33 L 30.40,79.05 L 30.91,79.80 L 31.39,80.56 "
    "L 31.91,81.30 L 32.41,82.05 L 32.81,82.84 L 33.32,83.59 L 33.77,84.36 L 34.14,85.17 "
    "L 34.55,85.96 L 34.94,86.76 L 35.34,87.55 L 35.74,88.34 L 36.13,89.14 L 36.53,89.93 "
    "L 36.94,90.72 L 37.28,91.54 L 37.58,92.38 L 37.96,93.18 L 38.04,94.10 L 38.29,94.95 "
    "L 38.79,95.71 L 39.02,96.57 L 39.24,97.44 L 39.40,98.33 L 39.72,99.16 L 39.84,100.07 "
    "L 40.10,100.92 L 40.21,101.83 L 40.45,102.69 L 40.47,103.64 L 40.75,104.48 L 40.79,105.42 "
    "L 41.01,106.29 L 41.15,107.19 L 41.11,108.17 L 41.10,109.13 L 41.23,110.03 L 41.49,110.89 "
    "L 41.46,111.86 L 41.45,112.82 L 41.45,113.78 L 41.46,114.73 L 41.46,115.69 L 41.46,116.65 "
    "L 41.45,117.61 L 41.46,118.57 L 41.43,119.51 L 41.09,120.34 L 41.12,121.30 L 41.13,122.27 "
    "L 41.05,123.20 L 40.80,124.05 L 40.72,124.97 L 40.40,125.80 L 40.44,126.77 L 40.13,127.62 "
    "L 40.08,128.52 L 40.03,129.54 L 40.56,130.00 L 40.77,129.19 L 41.15,128.40 L 41.45,127.56 "
    "L 41.78,126.74 L 42.12,125.92 L 42.41,125.08 L 42.57,124.19 L 42.87,123.36 L 43.11,122.50 "
    "L 43.34,121.63 L 43.54,120.76 L 43.51,119.79 L 43.76,118.93 L 44.17,118.14 L 44.29,117.23 "
    "L 44.58,116.40 L 44.61,115.45 L 44.95,114.63 L 44.90,113.65 L 45.26,112.84 L 45.25,111.88 "
    "L 45.62,111.07 L 45.57,110.10 L 45.86,109.26 L 45.93,108.33 L 46.22,107.49 L 46.27,106.55 "
    "L 46.43,105.66 L 46.64,104.79 L 46.63,103.82 L 46.62,102.86 L 46.88,102.01 L 46.99,101.10 "
    "L 46.99,100.14 L 46.97,99.18 L 46.97,98.21 L 46.97,97.25 L 46.98,96.29 L 46.98,95.34 "
    "L 46.98,94.38 L 46.98,93.42 L 46.97,92.47 L 46.96,91.51 L 47.00,90.53 L 46.97,89.59 "
    "L 46.65,88.76 L 46.65,87.80 L 46.63,86.86 L 46.31,86.03 L 46.34,85.06 L 46.05,84.22 "
    "L 45.96,83.30 L 45.84,82.39 L 45.56,81.55 L 45.27,80.71 L 45.00,79.86 L 44.71,79.02 "
    "L 44.43,78.18 L 44.16,77.33 L 43.81,76.52 L 43.40,75.73 L 43.10,74.90 L 42.79,74.07 "
    "L 42.31,73.30 L 41.82,72.55 L 41.41,71.76 L 40.91,71.01 L 40.39,70.26 L 39.91,69.51 "
    "L 39.41,68.75 L 38.85,68.03 L 38.30,67.30 L 37.77,66.56 L 37.21,65.83 L 36.60,65.12 "
    "L 36.02,64.41 L 35.43,63.69 L 34.81,62.99 L 34.19,62.29 L 33.59,61.58 L 33.02,60.86 "
    "L 32.40,60.15 L 31.69,59.49 L 30.99,58.82 L 30.45,58.09 L 29.92,57.35 L 29.23,56.67 "
    "L 28.53,56.01 L 27.88,55.31 L 27.30,54.60 L 26.76,53.86 L 26.22,53.13 L 25.66,52.40 "
    "L 25.12,51.67 L 24.63,50.91 L 24.21,50.12 L 23.82,49.33 L 23.42,48.53 L 23.03,47.74 "
    "L 22.63,46.94 L 22.22,46.16 L 21.88,45.34 L 21.57,44.51 L 21.38,43.63 L 21.16,42.76 "
    "L 21.09,41.82 L 21.09,40.87 L 21.12,39.91 L 21.12,38.95 L 21.09,37.98 L 21.08,37.02 "
    "L 21.13,36.08 L 21.28,35.18 L 21.52,34.32 L 21.74,33.46 L 21.93,32.58 L 22.23,31.74 "
    "L 22.57,30.93 L 22.99,30.14 L 23.38,29.34 L 23.78,28.55 L 24.17,27.76 L 24.58,26.96 "
    "L 25.07,26.21 L 25.59,25.46 L 26.07,24.71 L 26.58,23.96 L 27.12,23.22 L 27.67,22.49 "
    "L 28.23,21.76 L 28.77,21.03 L 29.32,20.30 L 29.86,19.57 L 30.44,18.85 L 31.12,18.17 "
    "L 31.84,17.51 L 32.50,16.83 L 33.05,16.09 L 33.65,15.38 L 34.25,14.67 L 34.75,13.92 "
    "L 35.40,13.24 L 35.95,12.50 L 36.47,11.76 L 37.07,11.05 L 37.32,10.16 L 36.71,10.00 Z"
)


def _parse_svg_points(d_str: str) -> list[tuple[float, float]]:
    pts = []
    tokens = d_str.replace(",", " ").split()
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("M", "L"):
            pts.append((float(tokens[i + 1]), float(tokens[i + 2])))
            i += 3
        else:
            i += 1
    return pts


def generate_orion_point_cloud() -> np.ndarray:
    """
    Parses Orion visage contours and produces a structured (N, 6) float32 3D spherical point cloud:
    Columns: [x0, y0, z0, role, phase, dist]
      - Front Visage: [x0, y0] normalized from SVG contours and mapped onto the front hemisphere (z0 > 0)
      - Volumetric Body & Shell: 3D sphere filling internal volume (R <= 0.95) and surface shell (R ~ 1.0)
      - role: 1.0 (visage perimeter), 0.0 (visage interior), 2.0 (spherical body / shell)
      - phase: Random phase seed [0, 2pi]
      - dist: Radial distance from origin
    """
    raw_left = _parse_svg_points(ORION_PATH_LEFT)
    raw_right = [(100.0 - x, y) for x, y in raw_left]

    poly_l = QPolygonF([QPointF(x, y) for x, y in raw_left])
    poly_r = QPolygonF([QPointF(x, y) for x, y in raw_right])

    path = QPainterPath()
    path.addPolygon(poly_l)
    path.closeSubpath()
    path.addPolygon(poly_r)
    path.closeSubpath()

    particles = []

    # 1. Perimeter Edge Particles (role = 1.0)
    for x, y in raw_left + raw_right:
        particles.append((x, y, 1.0))

    # Resample interpolated contour points for maximum sharpness
    def _resample_poly(pts: list[tuple[float, float]], target_n: int = 400):
        res = []
        n_orig = len(pts)
        for i in range(target_n):
            idx = (i / target_n) * (n_orig - 1)
            i0 = int(idx)
            i1 = min(i0 + 1, n_orig - 1)
            frac = idx - i0
            x = pts[i0][0] + frac * (pts[i1][0] - pts[i0][0])
            y = pts[i0][1] + frac * (pts[i1][1] - pts[i0][1])
            res.append((x, y, 1.0))
        return res

    particles.extend(_resample_poly(raw_left, target_n=250))
    particles.extend(_resample_poly(raw_right, target_n=250))

    # 2. Interior Cybernetic Lattice Particles (role = 0.0)
    rng = np.random.RandomState(42)
    step = 1.25
    for u in np.arange(10.0, 90.0, step):
        for v in np.arange(10.0, 130.0, step):
            uj = u + rng.uniform(-0.25, 0.25)
            vj = v + rng.uniform(-0.25, 0.25)
            if path.contains(QPointF(uj, vj)):
                particles.append((uj, vj, 0.0))

    # Normalize to Front Hemisphere of 3D Sphere (centered at 50, 70, scale by 72.0)
    arr = np.empty((len(particles), 6), dtype=np.float32)
    for i, (u, v, role) in enumerate(particles):
        x0 = (u - 50.0) / 72.0
        y0 = -(v - 70.0) / 72.0  # invert so +Y is up

        # Project 2D visage contours onto 3D spherical dome (Z > 0)
        r_xy2 = x0 * x0 + y0 * y0
        z_sphere = math.sqrt(max(0.04, 1.0 - min(0.96, r_xy2)))
        rim = 0.035 if role >= 0.5 else 0.010
        z0 = z_sphere + rim

        phase = rng.uniform(0.0, 2.0 * math.pi)
        dist = math.sqrt(x0 * x0 + y0 * y0 + z0 * z0)
        arr[i] = (x0, y0, z0, role, phase, dist)

    # 3. 3D Volumetric Spherical Body & Surface Shell (role = 2.0)
    # The particle effect IS the volumetric body of the sphere, colored in deep obsidian/cyber-navy
    n_vol = 1100
    vol_arr = np.empty((n_vol, 6), dtype=np.float32)
    for i in range(n_vol):
        u_rad = rng.uniform(0.005, 1.0)
        r = 0.94 * (u_rad ** (1.0 / 3.0))
        cos_phi = rng.uniform(-1.0, 1.0)
        sin_phi = math.sqrt(max(0.0, 1.0 - cos_phi * cos_phi))
        theta = rng.uniform(0.0, 2.0 * math.pi)
        bx = r * sin_phi * math.cos(theta)
        by = r * sin_phi * math.sin(theta)
        bz = r * cos_phi
        role = 2.0
        b_phase = rng.uniform(0.0, 2.0 * math.pi)
        b_dist = math.sqrt(bx * bx + by * by + bz * bz)
        vol_arr[i] = (bx, by, bz, role, b_phase, b_dist)

    n_shell = 600
    shell_arr = np.empty((n_shell, 6), dtype=np.float32)
    golden_ratio = (1.0 + math.sqrt(5.0)) / 2.0
    golden_angle = 2.0 * math.pi * (1.0 - 1.0 / golden_ratio)
    for i in range(n_shell):
        sy = 1.0 - (i / float(n_shell - 1)) * 2.0
        s_radius = math.sqrt(max(0.0, 1.0 - sy * sy))
        s_theta = golden_angle * i
        r_jitter = rng.uniform(0.97, 1.01)
        sx = s_radius * math.cos(s_theta) * r_jitter
        sy_j = sy * r_jitter
        sz = s_radius * math.sin(s_theta) * r_jitter
        role = 2.0
        s_phase = rng.uniform(0.0, 2.0 * math.pi)
        s_dist = math.sqrt(sx * sx + sy_j * sy_j + sz * sz)
        shell_arr[i] = (sx, sy_j, sz, role, s_phase, s_dist)

    return np.vstack([arr, vol_arr, shell_arr])


VERTEX_SHADER_SRC = """#version 330 core
layout(location = 0) in vec3 a_position;
layout(location = 1) in float a_role;  // 1.0=perimeter contour, 0.0=interior face, 2.0=spherical body/shell
layout(location = 2) in float a_phase;
layout(location = 3) in float a_dist;

uniform mat4 u_mvp;
uniform float u_time;
uniform float u_audio;
uniform int u_state; // 0=IDLE, 1=LISTENING, 2=SPEAKING, 3=MUTED

out vec3 v_color;
out float v_alpha;

void main() {
    vec3 p = a_position;
    vec3 animated_pos = p;

    if (a_role >= 1.5) {
        // 1. 3D SPHERICAL BODY OF ORION:
        // Swirling internal fluid vortex filling the sphere.
        // No left-to-right sway; particles orbit smoothly around the vertical Y-axis
        // with differential rotation and convective vertical circulation inside the sphere.
        float rxz = length(vec2(p.x, p.z));
        float psi = atan(p.z, p.x);

        float swirl_speed = (u_state == 1) ? 1.6 : 0.85;
        // Differential angular velocity (faster near equatorial core, smooth taper at poles)
        float ang_vel = swirl_speed * (0.80 + 0.35 * cos(p.y * 1.4));
        float new_psi = psi + ang_vel * u_time + a_phase * 0.15;

        // Toroidal & convective vertical pulsation within the sphere
        float dy = 0.032 * sin(2.0 * new_psi + u_time * 1.5 + a_phase);
        float new_y = clamp(p.y + dy, -0.98, 0.98);

        float new_x = rxz * cos(new_psi);
        float new_z = rxz * sin(new_psi);

        // Keep strictly within spherical boundary R <= 1.02
        vec3 cand_pos = vec3(new_x, new_y, new_z);
        float len_cand = length(cand_pos);
        if (len_cand > 1.02) {
            cand_pos = (cand_pos / len_cand) * 1.015;
        }
        animated_pos = cand_pos;
    } else {
        // 2. FOREGROUND CYBERNETIC VISAGE ON SPHERE SURFACE:
        // Projected onto front hemisphere. Particles swirl along internal streamlines to form the logo.
        // No left-to-right swerve! Dynamic fluid vortex forming the face.
        float r_xy = length(p.xy);
        float theta = atan(p.y, p.x);

        float swirl_rate = (u_state == 1) ? 2.5 : 1.2;
        float flow_phase = swirl_rate * u_time + a_phase + r_xy * 3.2;

        vec2 tangential = vec2(-sin(theta), cos(theta));
        vec2 radial = vec2(cos(theta), sin(theta));

        float swirl_amp = (a_role >= 0.5) ? 0.014 : 0.028;
        float radial_amp = (a_role >= 0.5) ? 0.008 : 0.018;

        vec2 swirl_flow = tangential * (swirl_amp * sin(flow_phase))
                        + radial * (radial_amp * cos(flow_phase * 0.8));

        float breath = 1.0 + 0.014 * sin(1.6 * u_time);
        animated_pos.xy = (p.xy + swirl_flow) * breath;
        animated_pos.z = p.z + 0.020 * sin(flow_phase + 1.57);

        // Conform visage to front spherical curvature
        float current_r = length(animated_pos.xy);
        if (current_r < 0.98) {
            float sphere_z = sqrt(max(0.04, 1.0 - current_r * current_r));
            animated_pos.z = mix(animated_pos.z, sphere_z + (a_role >= 0.5 ? 0.035 : 0.01), 0.65);
        }
    }

    // Audio reactive displacement in speaking mode
    if (u_state == 2 && u_audio > 0.01) {
        float d_vocal = length(vec2(p.x, p.y + 0.25));
        float wave = u_audio * (0.045 * sin(16.0 * d_vocal - 18.0 * u_time) + 0.020 * cos(8.0 * p.y + a_phase));
        animated_pos += normalize(p + vec3(0.001)) * wave;
    }

    gl_Position = u_mvp * vec4(animated_pos, 1.0);

    // Color and Alpha classification across the 3 layers:
    vec3 col;
    float alpha;
    float pt_size;

    if (a_role >= 1.5) {
        // Spherical Body: Darker background color of Orion's logo (deep midnight cyber-navy / obsidian cyan)
        // Matches #06090F base and #0A2540 / #0B324D glow from Orion dashboard
        vec3 dark_base = vec3(0.024, 0.055, 0.095);   // deep obsidian base #060e18
        vec3 dark_glow = vec3(0.042, 0.165, 0.260);   // dark midnight cyan-navy glow #0b2a42
        vec3 dark_core = vec3(0.055, 0.250, 0.380);   // subtle illuminated cyber-glow #0e4061

        float t = sin(u_time * 2.0 + a_phase) * 0.5 + 0.5;
        col = mix(dark_base, mix(dark_glow, dark_core, t), 0.75);

        float depth_fade = clamp(1.0 + animated_pos.z * 0.45, 0.30, 1.0);
        float r_norm = length(animated_pos);
        float edge_falloff = smoothstep(1.02, 0.88, r_norm);
        alpha = mix(0.35, 0.72, depth_fade) * edge_falloff;
        pt_size = mix(2.6, 4.4, t);
    } else if (a_role >= 0.5) {
        // Visage Perimeter Contours: Luminous intense electric cyan #59D4E6
        col = vec3(0.35, 0.88, 0.95);
        alpha = 0.95;
        pt_size = 5.2;
    } else {
        // Visage Interior Lattice: Electric cyan
        col = vec3(0.06, 0.68, 0.82);
        alpha = 0.72;
        pt_size = 3.8;
    }

    // State modulation
    if (u_state == 1) { // LISTENING
        float scan_y = mod(1.8 * u_time, 2.6) - 1.3;
        float scan_dist = abs(animated_pos.y - scan_y);
        float scan_glow = exp(-16.0 * scan_dist * scan_dist);
        col = mix(col, vec3(0.92, 1.0, 1.0), scan_glow * 0.85);
        alpha = clamp(alpha + scan_glow * 0.45, 0.0, 1.0);
        pt_size += scan_glow * 2.0;
    } else if (u_state == 2) { // SPEAKING
        float boost = clamp(u_audio * 1.5, 0.0, 1.0);
        col = mix(col, vec3(0.1, 0.95, 1.0), boost);
        alpha = clamp(alpha + boost * 0.35, 0.0, 1.0);
        pt_size += u_audio * 2.2;
    } else if (u_state == 3) { // MUTED
        col = vec3(0.20, 0.32, 0.38);
        alpha *= 0.45;
    }

    gl_PointSize = pt_size * (1.0 + animated_pos.z * 0.55);
    v_color = col;
    v_alpha = alpha;
}
"""

FRAGMENT_SHADER_SRC = """#version 330 core
in vec3 v_color;
in float v_alpha;
out vec4 fragColor;

void main() {
    vec2 coord = gl_PointCoord * 2.0 - 1.0;
    float r2 = dot(coord, coord);
    if (gl_PointCoord.x <= 0.001 && gl_PointCoord.y <= 0.001) {
        r2 = 0.0;
    } else if (r2 > 1.0) {
        discard;
    }

    // Dual-lobe radial falloff: hot sharp core + soft corona
    float core = exp(-r2 * 4.5);
    float halo = exp(-r2 * 1.8) * 0.55;
    float intensity = (core + halo) * v_alpha;

    vec3 final_rgb = mix(v_color, vec3(0.88, 1.0, 1.0), core * 0.55) * intensity;
    float final_alpha = clamp(intensity * 0.90, 0.0, 1.0);
    fragColor = vec4(final_rgb, final_alpha);
}
"""


class _GLVisageWidget(QOpenGLWidget):
    """Hardware accelerated OpenGL 3.3 Core Profile Visage Renderer."""

    def __init__(self, point_cloud: np.ndarray, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent; border: none;")
        self.points = point_cloud
        self.num_points = len(point_cloud)

        self.state_code = 0  # 0=IDLE, 1=LISTENING, 2=SPEAKING, 3=MUTED
        self.audio_level = 0.0
        self.start_time = time.monotonic()

        self.program: QOpenGLShaderProgram | None = None
        self.vbo: QOpenGLBuffer | None = None
        self.vao: QOpenGLVertexArrayObject | None = None

        self._gl_initialized = False

    def initializeGL(self):
        try:
            from OpenGL import GL as gl

            self.program = QOpenGLShaderProgram(self)
            self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, VERTEX_SHADER_SRC)
            self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, FRAGMENT_SHADER_SRC)
            if not self.program.link():
                raise RuntimeError(f"Shader link failed: {self.program.log()}")

            self.vao = QOpenGLVertexArrayObject()
            self.vao.create()
            self.vao.bind()

            self.vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
            self.vbo.create()
            self.vbo.bind()
            self.vbo.setUsagePattern(QOpenGLBuffer.UsagePattern.StaticDraw)
            self.vbo.allocate(self.points.tobytes(), self.points.nbytes)

            stride = 6 * 4  # 6 float32s = 24 bytes
            # location 0: vec3 a_position
            self.program.enableAttributeArray(0)
            self.program.setAttributeBuffer(0, gl.GL_FLOAT, 0, 3, stride)
            # location 1: float a_role
            self.program.enableAttributeArray(1)
            self.program.setAttributeBuffer(1, gl.GL_FLOAT, 12, 1, stride)
            # location 2: float a_phase
            self.program.enableAttributeArray(2)
            self.program.setAttributeBuffer(2, gl.GL_FLOAT, 16, 1, stride)
            # location 3: float a_dist
            self.program.enableAttributeArray(3)
            self.program.setAttributeBuffer(3, gl.GL_FLOAT, 20, 1, stride)

            self.vbo.release()
            self.vao.release()

            gl.glEnable(gl.GL_PROGRAM_POINT_SIZE)
            try:
                gl.glEnable(0x8861)  # GL_POINT_SPRITE
            except Exception:
                pass
            self._gl_initialized = True
        except Exception as e:
            print(f"[ORION VISAGE] OpenGL init failed, fallback needed: {e}")
            self._gl_initialized = False

    def resizeGL(self, w: int, h: int):
        try:
            from OpenGL import GL as gl
            gl.glViewport(0, 0, w, h)
        except Exception:
            pass

    def paintGL(self):
        if not self._gl_initialized or not self.program:
            return

        try:
            from OpenGL import GL as gl

            # Premultiplied alpha zero clear
            gl.glClearColor(0.0, 0.0, 0.0, 0.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)

            gl.glEnable(gl.GL_PROGRAM_POINT_SIZE)
            try:
                gl.glEnable(0x8861)  # GL_POINT_SPRITE
            except Exception:
                pass
            gl.glEnable(gl.GL_BLEND)
            # Premultiplied additive blend: perfect for Wayland compositing
            gl.glBlendFuncSeparate(
                gl.GL_ONE, gl.GL_ONE_MINUS_SRC_ALPHA, gl.GL_ONE, gl.GL_ONE_MINUS_SRC_ALPHA
            )

            now = float(time.monotonic() - self.start_time)
            w = max(1, self.width())
            h = max(1, self.height())
            aspect = w / h

            # Perspective-style MVP: ortho centered with slight aspect adjustment
            # zoom = 0.78 guarantees the entire 3D sphere floats within a diameter of 234px
            # inside the 300px window, with 33px transparent margins so no particle touches the edge.
            zoom = 0.78
            if aspect >= 1.0:
                mvp = np.diag([zoom / aspect, zoom, zoom * 0.5, 1.0]).astype(np.float32)
            else:
                mvp = np.diag([zoom, zoom * aspect, zoom * 0.5, 1.0]).astype(np.float32)

            self.program.bind()
            loc_mvp = self.program.uniformLocation("u_mvp")
            gl.glUniformMatrix4fv(loc_mvp, 1, gl.GL_FALSE, mvp)
            self.program.setUniformValue("u_time", now)
            self.program.setUniformValue("u_audio", float(self.audio_level))
            self.program.setUniformValue("u_state", int(self.state_code))

            self.vao.bind()
            gl.glDrawArrays(gl.GL_POINTS, 0, self.num_points)
            self.vao.release()
            self.program.release()
        except Exception as e:
            print(f"[ORION VISAGE] paintGL error: {e}")


class _SoftwareVisageWidget(QWidget):
    """Vectorized QPainter software renderer for headless or unsupported environments."""

    def __init__(self, point_cloud: np.ndarray, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.points = point_cloud
        self.num_points = len(point_cloud)

        self.state_code = 0
        self.audio_level = 0.0
        self.start_time = time.monotonic()

    def paintEvent(self, _):
        now = time.monotonic() - self.start_time
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        scale = min(w, h) * 0.38

        x0 = self.points[:, 0]
        y0 = self.points[:, 1]
        z0 = self.points[:, 2]
        role = self.points[:, 3]
        phase = self.points[:, 4]

        # 3D Spherical vortex swirl (NO left-to-right sway)
        is_body = role >= 1.5
        rxz = np.sqrt(x0 * x0 + z0 * z0)
        psi = np.arctan2(z0, x0)
        ang_vel = 0.85 * (0.80 + 0.35 * np.cos(y0 * 1.4))
        new_psi = psi + ang_vel * now + phase * 0.15
        dy = 0.032 * np.sin(2.0 * new_psi + now * 1.5 + phase)
        new_y = np.clip(y0 + dy, -0.98, 0.98)
        new_x = rxz * np.cos(new_psi)
        new_z = rxz * np.sin(new_psi)

        # Front visage flow along streamlines
        r_xy = np.sqrt(x0 * x0 + y0 * y0)
        theta = np.arctan2(y0, x0)
        flow_phase = 1.2 * now + phase + r_xy * 3.2
        swirl_amp = np.where(role >= 0.5, 0.014, 0.028)
        radial_amp = np.where(role >= 0.5, 0.008, 0.018)
        swirl_x = -np.sin(theta) * (swirl_amp * np.sin(flow_phase)) + np.cos(theta) * (radial_amp * np.cos(flow_phase * 0.8))
        swirl_y = np.cos(theta) * (swirl_amp * np.sin(flow_phase)) + np.sin(theta) * (radial_amp * np.cos(flow_phase * 0.8))

        breath = 1.0 + 0.014 * math.sin(1.6 * now)
        fx = np.where(is_body, new_x, (x0 + swirl_x) * breath)
        fy = np.where(is_body, new_y, (y0 + swirl_y) * breath)

        px = cx + fx * scale
        py = cy - fy * scale  # screen Y is inverted

        color_body = QColor(10, 37, 64, 115)       # deep midnight cyber-navy #0a2540
        color_edge = QColor(89, 212, 230, 225)     # electric cyan #59d4e6
        color_fill = QColor(15, 173, 209, 150)     # cyan fill

        # Batch draw points
        for i in range(self.num_points):
            r_val = role[i]
            if r_val >= 1.5:
                r_pt = 1.8
                c = color_body
            elif r_val > 0.5:
                r_pt = 2.4
                c = color_edge
            else:
                r_pt = 1.5
                c = color_fill
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c)
            p.drawEllipse(QPointF(px[i], py[i]), r_pt, r_pt)

        p.end()




class OrionParticleCanvas(QWidget):
    """
    Main Orion Visage Canvas.
    Encapsulates OpenGL and software renderers, provides API parity with legacy HudCanvas,
    and implements pointer drag vs click disambiguation.
    """

    visageClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent; border: none;")
        self.setMinimumSize(240, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._points = generate_orion_point_cloud()
        self.speaking = False
        self.muted = False
        self.state = "INITIALISING"
        self._audio_level = 0.0

        # Disambiguation state
        self._press_global_pos = None
        self._press_win_pos = None
        self._press_time = 0.0
        self._is_dragging = False

        # Renderer selection
        force_software = os.getenv("ORION_RENDERER", "").lower() == "software"
        if not force_software:
            self._renderer = _GLVisageWidget(self._points, self)
        else:
            self._renderer = _SoftwareVisageWidget(self._points, self)

        # 60 FPS animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._renderer.setGeometry(0, 0, event.size().width(), event.size().height())

    def _tick(self):
        # Audio decay
        if self.speaking:
            target_level = np.random.uniform(0.35, 0.95)
            self._audio_level += (target_level - self._audio_level) * 0.35
        else:
            self._audio_level *= 0.85

        self._renderer.audio_level = self._audio_level
        self._renderer.update()

    # --- API Parity with Legacy HudCanvas ---
    def set_state(self, state: str):
        self.state = state
        self.speaking = state == "SPEAKING"
        if self.muted:
            self._renderer.state_code = 3
        elif state == "SPEAKING":
            self._renderer.state_code = 2
        elif state in ("LISTENING", "PROCESSING"):
            self._renderer.state_code = 1
        else:
            self._renderer.state_code = 0

    def set_speaking(self, speaking: bool):
        self.speaking = speaking
        if self.speaking:
            self.set_state("SPEAKING")
        elif self.state == "SPEAKING":
            self.set_state("IDLE")

    def set_muted(self, muted: bool):
        self.muted = muted
        self.set_state(self.state)

    def set_audio_level(self, level: float):
        self._audio_level = max(0.0, min(1.0, level))
        self._renderer.audio_level = self._audio_level

    # --- Mouse Gesture Disambiguation (Drag-to-Move vs. Click-to-Toggle) ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global_pos = event.globalPosition().toPoint()
            win = self.window()
            self._press_win_pos = win.frameGeometry().topLeft()
            self._press_time = time.monotonic()
            self._is_dragging = False
            self._is_double_click = False
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_double_click = True
            win = self.window()
            if win:
                if win.isMaximized() or win.isFullScreen():
                    if hasattr(win, "set_hud_expanded"):
                        win.set_hud_expanded(False)
                    elif hasattr(win, "_toggle_maximize"):
                        win._toggle_maximize()
                elif hasattr(win, "_toggle_maximize"):
                    win._toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_global_pos is not None:
            delta = event.globalPosition().toPoint() - self._press_global_pos
            if delta.manhattanLength() >= 4:
                self._is_dragging = True
                win = self.window()
                # On native Wayland, delegate dragging directly to compositor when not maximized/fullscreen
                if not win.isMaximized() and not win.isFullScreen():
                    wh = win.windowHandle()
                    if wh and QGuiApplication.platformName() == "wayland":
                        wh.startSystemMove()
                        self._press_global_pos = None
                        return
                    elif QGuiApplication.platformName() != "wayland":
                        win.move(self._press_win_pos + delta)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if getattr(self, '_is_double_click', False):
                self._is_double_click = False
            else:
                elapsed = time.monotonic() - getattr(self, '_press_time', 0.0)
                if not getattr(self, '_is_dragging', False) and elapsed <= 0.35:
                    self.visageClicked.emit()
            self._press_global_pos = None
            self._is_dragging = False
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self._press_global_pos = None
        super().leaveEvent(event)
