# Plan: O.R.I.O.N Minimalist 3D Visage & Interactive Glassmorphic HUD

## Long-Running Task Specification
- **Task ID:** ANUBIS-ORION-MINIMAL-UI-2026
- **Objective:** Redesign Orion's desktop UI in `/home/grim/Downloads/Anubis` with a 3D cybernetic particle visage matching the Orion logo (`ORION_PATH_LEFT` & `ORION_PATH_RIGHT`), a frameless translucent aesthetic hiding window chrome and continuous metrics by default, an interactive click-to-reveal translucent HUD for controls (Activity Log, File Drop Zone, Command Input, Microphone Active, Window Controls), and on-demand voice/tool vitals routing.
- **Rules & Constraints:** 
  - Zero emojis in markdown files.
  - No continuous background CPU polling for vitals.
  - Native Wayland/COSMIC support with premultiplied alpha and drag-to-move disambiguation.
  - Durable task tracking in `PLAN.md`, `STATE.md`, `FINDINGS.md`, and `LEDGER.md`.

## Execution Epochs

### Epoch 1: 3D Visage Particle Engine (`orion_visage.py`)
- [x] Parse `ORION_PATH_LEFT` and `ORION_PATH_RIGHT` from `OrionLogo.tsx` / `~/.config/waybar/icons/orion.svg`.
- [x] Implement mathematical normalization, two-tier sampling (900 contour + 1,578 jittered interior), and 3D Z-curvature mapping.
- [x] Build `OrionParticleCanvas` with dual-backend support: `_GLVisageWidget` (QOpenGLWidget, GLSL 330 premultiplied alpha) and `_SoftwareVisageWidget` (vectorized QPainter fallback).
- [x] Implement pointer state machine (distinguishing drag-to-move via `startSystemMove` from click-to-toggle).
- [x] Unit test vertex generation, geometry bounds, and canvas lifecycle in isolation.

### Epoch 2: On-Demand Vitals Engine (`vitals.py` & `main.py`)
- [x] Implement `vitals.py` with `collect_system_vitals(focus)` (on-demand snapshot, zero continuous thread).
- [x] Declare `get_system_vitals` tool in `TOOL_DECLARATIONS` in `main.py`.
- [x] Implement tool execution handler returning structured telemetry for speech synthesis.
- [x] Add `vitalsUpdated` signal / `show_vitals_toast` to UI bridge for temporary floating HUD toast.

### Epoch 3: Frameless Glassmorphic HUD & Window State Machine (`ui.py`)
- [x] Configure `QSurfaceFormat` (8-bit alpha) prior to `QApplication` instantiation.
- [x] Update `MainWindow` to `FramelessWindowHint | WindowStaysOnTopHint | WA_TranslucentBackground`.
- [x] Remove legacy continuous `_left_panel` (`MetricBar` widgets) and continuous metric timers.
- [x] Build `GlassHeaderWidget` (`_ [] X`, clock) and `GlassPanelWidget` (Activity Log, File Drop Zone, Command Input, Mic Active, Fullscreen [F11]).
- [x] Build `VitalsToastOverlay` (6-second auto-fading glassmorphic toast).
- [x] Implement state machine: `COMPACT_ORB` (280x360 px, default on startup and wake word) <-> `EXPANDED_HUD` (780x540 px, revealed on visage click).

### Epoch 4: End-to-End Verification & Hardening
- [x] Run headless and live graphical tests under Wayland.
- [x] Test drag-to-move vs click-to-reveal gesture disambiguation.
- [x] Test wake word pop-up behavior (ensuring it stays in `COMPACT_ORB`).
- [x] Verify `get_system_vitals` voice tool execution and toast animation.
- [x] Audit for memory leaks, CPU consumption, and Wayland alpha artifacts.

### Epoch 5: 3D Spherical Geometry, Dark Logo Color Harmonization & Window Masking
- [x] Map Orion visage contours onto the front dome of a 3D unit sphere ($Z > 0$) in electric cyan `#59D4E6`.
- [x] Structure the background particle effect into the 3D volumetric body ($R \le 0.95$) and surface Fibonacci shell ($R \approx 1.0$) of the sphere.
- [x] Harmonize body particle colors with Orion logo background colors from dashboard (`#06090F` base, `#0A2540` / `#0B324D` cyber-navy glow).
- [x] Implement spherical differential vortex kinematics (rotation about vertical $Y$-axis with internal convective circulation; zero left-to-right sway).
- [x] Apply circular `QRegion` ellipse masking in compact mode ($300 \times 300$ px) to hide all rectangular window edges and borders, restoring rectangular layout on HUD expansion.
- [x] Validate via unit tests and graphical framebuffer captures.

### Epoch 6: Dark Mode Contrast Theming & Upload/Minimize Layout Collision Resolution
- [x] Enforce luminous high-contrast `QPalette` (`Window`: `#0b1522`, `Base`: `#08101a`, `Text`/`WindowText`: `#e0f6fc`, `Placeholder`: `#5ab8cc`, `Highlight`: `#00b4e6`) and comprehensive `QFileDialog` dark stylesheet across all standard Qt views.
- [x] Eliminate unreadable black-on-black text in standard file picker file and folder listings.
- [x] Brighten secondary HUD labels (`_file_hint`, `_date_lbl`, `sub`, file list types) to `#7ec7d8` and `#00d4ff`.
- [x] Reparent `QFileDialog` to root window (`self.window()`) and enforce post-dialog geometry retention (`setMinimumSize(700, 480)`, `resize(820, 540)`).
- [x] Remap header minimize button (`–`) to `set_hud_expanded(False)` (collapsing HUD back to compact spherical orb instead of OS taskbar minimize).
- [x] Harden `changeEvent` against Wayland modal state desynchronization using deferred timer.
- [x] Validate via unit tests (27/27 passing), restart `anubis.service`, and verify visual captures.
