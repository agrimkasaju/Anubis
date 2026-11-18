# Ledger of Changes

| Timestamp | Phase | Target File | Change Summary |
| :--- | :--- | :--- | :--- |
| 2026-11-17T21:07 | Init | PLAN.md, STATE.md, FINDINGS.md, LEDGER.md | Initialized long-running task documentation artifacts. |
| 2026-11-17T21:09 | Epoch 1 | orion_visage.py, tests/test_orion_visage.py | Created 3D particle visage engine from Orion SVG curves with dual OpenGL/software backends, 4/4 passing unit tests. |
| 2026-11-17T21:10 | Epoch 2 | vitals.py, main.py, tests/test_vitals.py | Implemented on-demand vitals engine, registered get_system_vitals in TOOL_DECLARATIONS with execution dispatch, 2/2 passing tests. |
| 2026-11-17T21:20 | Epoch 3 | ui.py, tests/test_ui_minimal.py | Rebuilt MainWindow with translucent frameless window, COMPACT_ORB vs EXPANDED_HUD state machine, removed continuous polling, added GlassHeaderWidget, GlassPanelWidget, and VitalsToastOverlay. |
| 2026-11-17T21:30 | Epoch 4 | orion_visage.py, tests/ | Resolved GL_POINT_SPRITE and mouse transparency handling, tuned particle point size and falloff, verified click-to-expand and drag disambiguation, verified on-demand vitals voice tool execution. Full suite 24/24 passing. |
| 2026-11-17T21:41 | Living Field | orion_visage.py, tests/test_orion_visage.py | Integrated Ortho-grade living kinematics: 950-particle orbital background corona behind Orion, continuous 3D curl-noise vector field turbulence, and pulsing synaptic filaments (GL_LINES). Suite 25/25 passing. Restarted anubis.service. |
| 2026-11-17T21:56 | Swirl & Window Fixes | orion_visage.py, ui.py, tests/ | Removed wireframe synapse cage artifacts from eye/visor cutout; replaced rigid left-right sway with continuous vortex swirl stream kinematics forming the logo; resolved maximize/minimize window geometry collision by restoring normal state prior to compact sizing and enforcing layout bounds. Full suite 25/25 passing. Restarted anubis.service (PID 1728404). |
| 2026-11-17T22:20 | Spherical Orb & Logo Body | orion_visage.py, ui.py, tests/ | Structured Orion as a 3D sphere with 1,700 volumetric body and Fibonacci shell particles colored in deep obsidian/cyber-navy (#06090F / #0A2540) matching the Orion dashboard; mapped visage contours to front hemisphere in electric cyan (#59D4E6); applied circular QRegion ellipse mask in compact orb mode (300x300 px) to eliminate all rectangular outer borders and window boxes; added mask assertions to test_ui_minimal.py. Full suite 25/25 passing. |
| 2026-11-17T22:38 | Epoch 6: Dark Mode & Layout | ui.py, tests/test_ui_minimal.py | Added setup_dark_app_theme with high-contrast QPalette and QFileDialog stylesheet; fixed black-on-black text in file picker; brightened secondary labels across HUD; reparented QFileDialog to MainWindow with geometry enforcement; remapped header minimize button to set_hud_expanded(False); hardened changeEvent against Wayland modal squishing. Full suite 27/27 passing. Restarted anubis.service (PID 2369648). |
| 2026-11-17T22:43 | Epoch 7: Repository Organization | doc/, actions/vitals.py, main.py, ui.py, tests/test_vitals.py | Relocated vitals.py into actions/vitals.py and updated all module imports across main.py, ui.py, and tests/test_vitals.py; moved task tracking markdown files (PLAN.md, STATE.md, FINDINGS.md, LEDGER.md) into doc/ directory. Full suite 27/27 passing. Restarted anubis.service. |



