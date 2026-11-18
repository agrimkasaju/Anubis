# State: O.R.I.O.N Minimalist 3D Visage & Interactive Glassmorphic HUD

## Current Status
- **Active Epoch:** Epoch 13 Complete (Wayland Surface Clamping, Maximize State Decoupling, and Background Resume Pop-Up Prevention)
- **Current Objective:** Eliminate Wayland compositor surface retention and invisible box offsets on minimized Orion; decouple maximize/fullscreen state so unmaximizing from compact mode reverts directly to 300x300 px compact orb; eliminate uninvited GUI pop-ups (`bring_to_front()`) during background resume/job compilation; enforce strictly aligned compact visage layout with zero pointer drift.
- **Current Blockers:** None.
- **Runtime Environment:** Pop!_OS Linux (COSMIC Desktop, Wayland), Python 3.11, PyQt6, PyOpenGL 3.1.9.

## Component States
- `ui.py` (`MainWindow`, `JarvisUI`): Completed & Verified (Tracked `_maximized_from_compact` state flag across `_toggle_maximize`, `_toggle_fullscreen`, and `_handle_escape` to return directly to compact orb mode when maximized from compact mode; removed destructive `self.showNormal()` call from `bring_to_front()` that restored pre-maximize 820x540 dimensions; anchored `_visage_container` to top-left in compact mode and center in expanded mode; enforced `setFixedSize(300, 300)`, `resize(300, 300)`, and `wh.resize(300, 300)` across state transitions with multi-stage singleShot backup guards).
- `main.py` (`JobWatcher`): Completed & Verified (Removed automatic UI wake-up / `bring_to_front()` from background job discovery and resume compilation loop, keeping notification vocal/background only without stealing desktop focus).
- `orion_visage.py`: Completed & Verified (Updated `mouseDoubleClickEvent` to collapse directly to compact orb mode via `set_hud_expanded(False)` when double-clicked while maximized or fullscreen).
- `actions/web_search.py`: Completed & Verified (Resilient DDG search with token sanitization and fallback query execution).
- `actions/calendar_job_sync.py`: Completed & Verified (Daily digest synchronization engine with automated stale digest event deletion).
- `tests/test_ui_minimal.py`: 17/17 Passing
- `tests/test_orion_visage.py`: 8/8 Passing
- `tests/test_calendar_job_sync.py`: 3/3 Passing
- `tests/test_vitals.py`: 3/3 Passing
- Entire Anubis Suite: 42/42 Passing in 4.56s
