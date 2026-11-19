# State: O.R.I.O.N Minimalist 3D Visage & Interactive Glassmorphic HUD

## Current Status
- **Active Epoch:** Epoch 14 Complete (Wayland XDG Surface Clamping and Asynchronous Resize Timer Guarding)
- **Current Objective:** Eliminate Wayland compositor surface retention and invisible box offsets on minimized Orion; decouple maximize/fullscreen state so unmaximizing from compact mode reverts directly to 300x300 px compact orb; eliminate uninvited GUI pop-ups (`bring_to_front()`) during background resume/job compilation; enforce strictly aligned compact visage layout with zero pointer drift.
- **Current Blockers:** None.
- **Runtime Environment:** Pop!_OS Linux (COSMIC Desktop, Wayland), Python 3.11, PyQt6, PyOpenGL 3.1.9.

## Component States
- `ui.py` (`MainWindow`, `JarvisUI`): Completed & Verified (Guarded all asynchronous resize lambdas in `changeEvent` and `resizeEvent` with `if self._hud_expanded and not self.isMaximized() and not self.isFullScreen()` checks to prevent post-collapse expansion to 820x540; implemented Wayland unmap/remap surface cycling (`hide()` -> apply geometry -> `show()`) in `set_hud_expanded(False)`, `changeEvent`, and `resizeEvent` to force `cosmic-comp` to destroy lingering 820x540 surfaces; synchronously clamped `centralWidget()` to 300x300 px; centered visage layout in both modes).
- `main.py` (`JobWatcher`): Completed & Verified (Removed automatic UI wake-up / `bring_to_front()` from background job discovery and resume compilation loop, keeping notification vocal/background only without stealing desktop focus).
- `orion_visage.py`: Completed & Verified (Updated `mouseDoubleClickEvent` to collapse directly to compact orb mode via `set_hud_expanded(False)` when double-clicked while maximized or fullscreen).
- `actions/web_search.py`: Completed & Verified (Resilient DDG search with token sanitization and fallback query execution).
- `actions/calendar_job_sync.py`: Completed & Verified (Daily digest synchronization engine with automated stale digest event deletion).
- `tests/test_ui_minimal.py`: 18/18 Passing
- `tests/test_orion_visage.py`: 8/8 Passing
- `tests/test_calendar_job_sync.py`: 3/3 Passing
- `tests/test_vitals.py`: 3/3 Passing
- Entire Anubis Suite: 43/43 Passing in 4.64s
