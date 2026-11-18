# State: O.R.I.O.N Minimalist 3D Visage & Interactive Glassmorphic HUD

## Current Status
- **Active Epoch:** Epoch 8 Complete (Spherical Viewport Containment, Wayland Native Dragging, and Zero Mask Clipping)
- **Current Objective:** Spherical visage floating without black rectangular mask clipping; smooth compositor-delegated dragging restored.
- **Current Blockers:** None.
- **Runtime Environment:** Pop!_OS Linux (COSMIC Desktop, Wayland), Python 3.11, PyQt6, PyOpenGL 3.1.9.

## Component States
- `orion_visage.py`: Completed & Verified (3D spherical point cloud with 1,700 volumetric body and Fibonacci shell particles in dark midnight cyber-navy #06090F / #0A2540 + front dome visage in electric cyan #59D4E6; GLSL 330 differential vortex kinematics; viewport zoom adjusted to 0.78 ensuring full 3D sphere containment inside 234px diameter within 300px window; smoothstep radial alpha edge falloff; WA_AlwaysStackOnTop and transparent styles configured).
- `actions/vitals.py`: Completed & Verified (Instantaneous snapshot collector under 160ms with zero continuous threads, housed under actions/).
- `main.py` (`TOOL_DECLARATIONS` & tool handler): Completed & Verified (Native Wayland session retained; registered `get_system_vitals`, wired to toast overlay and synthesized spoken summary).
- `ui.py` (`MainWindow` & Glassmorphic HUD): Completed & Verified (Pure alpha transparency on native Wayland without destructive 1-bit setMask clipping that created black borders; wh.startSystemMove restored for smooth compositor window dragging; seamless expansion to 820x540 px HUD on click; high-contrast dark theme setup_dark_app_theme fixing QFileDialog file list text; modal geometry retention; header minimize button wired to compact orb collapse).
- `tests/test_orion_visage.py`: 7/7 Passing
- `tests/test_ui_minimal.py`: 8/8 Passing
- `tests/test_vitals.py`: 3/3 Passing
- Entire Anubis Suite: 29/29 Passing in 3.18s

