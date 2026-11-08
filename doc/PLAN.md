# Long-Running Task Implementation Plan: Flight Price Poller & Tracker Engine

> **TASK MODE DECLARATION:**  
> This document represents the execution plan for a **long-running task**. Maintained records in `~/Downloads/Anubis/`:
> - `PLAN.md` (this file, task objectives, phases, and acceptance criteria)
> - `STATE.md` (execution epochs and active runtime state)
> - `FINDINGS.md` (discovery evidence, benchmark timings, and baggage pricing analysis)
> - `LEDGER.md` (execution history and verification checkpoints)

---

## 1. Executive Summary & Objective

Implement an autonomous, background flight price polling and drop-detection engine for Anubis. When a user sets a reminder to monitor flight prices over a date range (e.g., *"track flights from Ottawa to Calgary with 1 carry-on until next Saturday"*), Anubis will:
1. Persist the tracking job with exact baggage filters (`carry_on`, `checked_bags`, or both).
2. Headlessly poll Google Flights twice daily (8:30 AM and 6:30 PM) without popping up browser windows or interrupting the user.
3. Apply the exact baggage filters in headless Chromium so prices reflect true all-inclusive fares.
4. Compare fares against `lowest_seen_price`; if a price drop occurs, fire a Linux desktop notification, audio chime, and Orion voice alert.
5. Automatically expire and terminate polling once the reminder end date is reached.

---

## 2. Acceptance Criteria
- [x] **Headless Scraper:** `scrape_flights_headless(...)` runs silently via Playwright Chromium without UI popups.
- [x] **Baggage Filter Enforcement:** Carry-on, checked bag, or both are applied during each poll, matching user specifications.
- [x] **Tracker Ledger:** JSON store at `data/flight_trackers.json` storing status, expiration, baggage params, baseline price, lowest seen price, and timestamped poll history.
- [x] **Drop-Only Alerts:** Notifications are dispatched ONLY on price drops; unchanged/higher prices are logged quietly.
- [x] **Auto-Expiration:** Polling stops when `datetime.now() > expires_at`.
- [x] **Reminder & Voice Integration:** Users can create and trigger flight tracking via voice/reminder commands.
- [x] **Anubis Background Daemon:** Background scheduler running inside `anubis.service` checks at 08:30 and 18:30.

---

## 3. Implementation Phases

- [x] **Phase 1: Headless Scraper Adapter (`actions/flight_finder.py`)**  
  Exported `scrape_flights_headless_async` and `scrape_flights_headless` using Playwright Chromium with `headless=True` reusing baggage and multi-leg card parsers.
- [x] **Phase 2: Flight Tracker CRUD Engine (`actions/flight_tracker.py`)**  
  Built `add_flight_tracker`, `poll_tracker`, `poll_all_active_trackers`, `list_flight_trackers`, `cancel_flight_tracker`, and `data/flight_trackers.json`.
- [x] **Phase 3: Background Poller Service (`services/flight_poller.py` & `main.py`)**  
  Created `FlightPollerDaemon` checking active trackers at 8:30 AM & 6:30 PM local time with Linux desktop alerts, registered in `main.py` task group.
- [x] **Phase 4: Reminder Integration & Tool Registration (`actions/reminder.py`, `main.py`, `agent/planner.py`, `core/prompt.txt`)**  
  Connected flight tracking to `reminder` action, registered `flight_tracker` tool schema, planner rules, and prompt instructions.
- [x] **Phase 5: Verification & End-to-End Testing**  
  Tested baseline creation, simulated price drops, verified baggage filtering, and confirmed `anubis.service` daemon launch.
