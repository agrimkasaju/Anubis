# State: O.R.I.O.N Minimalist 3D Visage & Interactive Glassmorphic HUD

## Current Status
- **Active Epoch:** Epoch 12 Complete (Wayland Surface Clamping & Fullscreen Collapse Mouse Tracking Synchronization)
- **Current Objective:** Eliminate Wayland compositor surface expansion into an invisible transparent box on the right of Orion when transitioning from fullscreen or maximized mode to compact orb mode; lock `MainWindow`, `_visage_container`, and `self.hud` strictly to fixed 300x300 px dimensions with zero margin/spacing offsets; route background thread wake-ups safely through Qt queued signals to eliminate cross-thread QOpenGLContext errors.
- **Current Blockers:** None.
- **Runtime Environment:** Pop!_OS Linux (COSMIC Desktop, Wayland), Python 3.11, PyQt6, PyOpenGL 3.1.9.

## Component States
- `ui.py` (`MainWindow`, `JarvisUI`): Completed & Verified (Enforced `setFixedSize(300, 300)` on MainWindow, `_visage_container`, and `self.hud` in `_apply_compact_orb_geometry`; zeroed `_body_layout` and `_root_layout` spacing and contents margins in compact mode; clamped surface geometry before calling `showNormal()` in `set_hud_expanded(False)`, `_toggle_maximize`, `_toggle_fullscreen`, and `_handle_escape` with singleShot backup guards; added thread-safe `_vitals_sig` and `wake_signal` properties in `JarvisUI`).
- `main.py` (`JobWatcher`): Completed & Verified (Updated automatic background job discovery wake-up sequence to emit `self.ui.wake_signal.emit()` safely across threads, preventing cross-thread `QOpenGLContext` conflicts).
- `orion_visage.py`: Completed & Verified (Compositor-delegated dragging via `wh.startSystemMove()` with zero coordinate offsets across fullscreen and compact cycles).
- `actions/web_search.py`: Completed & Verified (Resilient DDG search with token sanitization and fallback query execution).
- `actions/calendar_job_sync.py`: Completed & Verified (Daily digest synchronization engine with automated stale digest event deletion).
- `tests/test_ui_minimal.py`: 15/15 Passing
- `tests/test_orion_visage.py`: 8/8 Passing
- `tests/test_calendar_job_sync.py`: 3/3 Passing
- `tests/test_vitals.py`: 3/3 Passing
- Entire Anubis Suite: 40/40 Passing in 4.26s
