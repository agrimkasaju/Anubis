#!/usr/bin/env python3
"""
Orion Companion Dashboard (Desktop & Mobile PWA)
Auto-adapts between Desktop Command View and Mobile Touch View.
Secured via Token Authentication & Tailscale.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# --- DIRECTORY & ENVIRONMENT CONFIG ---
BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
API_KEYS_FILE = CONFIG_DIR / "api_keys.json"
ENV_FILE = BASE_DIR / ".env"

# Add Anubis and action paths to sys.path
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Load .env if present
if ENV_FILE.exists():
    try:
        for _line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))
    except Exception:
        pass


def _load_config() -> dict:
    if API_KEYS_FILE.exists():
        try:
            return json.loads(API_KEYS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


_config = _load_config()

PORT = int(os.getenv("DASHBOARD_PORT") or _config.get("dashboard_port") or 8088)


def get_tailscale_ip() -> str:
    ip = os.getenv("TAILSCALE_IP") or _config.get("tailscale_ip")
    if ip:
        return str(ip).strip()
    if shutil.which("tailscale"):
        try:
            res = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                detected = res.stdout.strip().splitlines()[0].strip()
                if detected:
                    return detected
        except Exception:
            pass
    return ""


TAILSCALE_IP = get_tailscale_ip()
REMOTE_LLM_HOST = str(os.getenv("REMOTE_LLM_HOST") or _config.get("remote_llm_host") or "").strip()

from job_bridge import bridge
import actions.stock_actions
# Suppress opening desktop browser tabs during dashboard stock calls
actions.stock_actions.open_dashboard = lambda: None
from actions.stock_actions import get_stock_analysis, ensure_llm_connected
from actions.web_search import _ddg_search, _format_ddg
from or_client import client


def get_or_create_token() -> str:
    """Retrieves token from .env or config/api_keys.json, or generates a persistent random one."""
    token = os.getenv("DASHBOARD_TOKEN") or _config.get("dashboard_token")
    if token:
        return str(token).strip()

    token = secrets.token_hex(8)
    _config["dashboard_token"] = token
    try:
        API_KEYS_FILE.write_text(json.dumps(_config, indent=4), encoding="utf-8")
        print(f"[Dashboard] 🔑 Generated new dashboard token: {token}")
    except Exception as e:
        print(f"[Dashboard] ⚠️ Failed to persist token: {e}")

    return token


AUTH_TOKEN = get_or_create_token()


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>Orion Companion Dashboard</title>
  <meta name="theme-color" content="#09090b">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: '#00d4ff',
            surface: '#12151e',
            panel: '#181b26',
            bordercol: '#232736'
          }
        }
      }
    }
  </script>
  <style>
    body {
      background-color: #09090b;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      padding-top: env(safe-area-inset-top);
      padding-bottom: env(safe-area-inset-bottom);
    }
    .custom-scroll::-webkit-scrollbar { width: 4px; height: 4px; }
    .custom-scroll::-webkit-scrollbar-thumb { background: #27272a; border-radius: 4px; }
  </style>
</head>
<body class="text-zinc-100 min-h-screen flex flex-col selection:bg-cyan-500 selection:text-black">

  <!-- TOP HEADER -->
  <header class="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur sticky top-0 z-50 px-4 py-3">
    <div class="max-w-6xl mx-auto flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></div>
        <span class="font-bold tracking-wider text-sm md:text-base text-zinc-100 uppercase">ORION <span class="text-cyan-400 font-mono">DASHBOARD</span></span>
      </div>

      <div class="flex items-center space-x-2">
        <span id="device-badge" class="hidden sm:inline-block px-2.5 py-0.5 text-xs font-medium rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
          Auto View
        </span>
        <button onclick="refreshAll()" class="px-2.5 py-1 text-xs rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition">
          🔄 Refresh
        </button>
      </div>
    </div>
  </header>

  <!-- MAIN CONTAINER (Auto Responsive Grid: 1 col on mobile, 2 cols on desktop) -->
  <main class="max-w-6xl mx-auto w-full p-4 md:p-6 flex-1 grid grid-cols-1 md:grid-cols-12 gap-6">

    <!-- LEFT COLUMN (7 Cols on Desktop): Job Bridge & Job Search Pipeline -->
    <div class="md:col-span-7 flex flex-col space-y-6">

      <!-- CARD 1: PENDING JOB APPLICATION BRIDGE -->
      <section id="job-card" class="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-5 shadow-lg relative overflow-hidden transition-all duration-300">
        <div class="flex items-center justify-between pb-3 border-b border-zinc-800/80">
          <div class="flex items-center space-x-2">
            <span class="text-lg">⚡</span>
            <h2 class="text-sm font-semibold tracking-wider text-zinc-300 uppercase">Job Application Bridge</h2>
          </div>
          <span id="bridge-status-pill" class="text-xs px-2.5 py-0.5 rounded-full bg-zinc-800 text-zinc-400">Polling...</span>
        </div>

        <!-- Empty State -->
        <div id="job-empty-state" class="py-8 text-center">
          <p class="text-zinc-500 text-sm">No pending job applications waiting for approval.</p>
          <p class="text-zinc-600 text-xs mt-1">When the framework compiles an application, review actions will appear here.</p>
        </div>

        <!-- Pending State -->
        <div id="job-pending-state" class="hidden pt-4 space-y-4">
          <div id="job-card-header" class="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3.5 transition-colors">
            <div id="job-stage-badge" class="text-xs font-mono uppercase tracking-wider text-amber-400 font-semibold">Ready for Review</div>
            <h3 id="job-title" class="text-lg font-bold text-white mt-0.5">Software Engineer</h3>
            <div id="job-company" class="text-sm font-medium text-zinc-300">Company Name</div>
            <a id="job-link" href="#" target="_blank" class="inline-block mt-2 text-xs text-cyan-400 underline hover:text-cyan-300">
              Open Job Posting ↗
            </a>
          </div>

          <!-- Tailored Application Documents (PDF Download / Preview) -->
          <div id="job-pdf-docs" class="space-y-1.5">
            <div class="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Generated Application Documents</div>
            <div class="grid grid-cols-3 gap-2 text-xs">
              <a id="pdf-resume-link" href="#" target="_blank" class="py-2.5 px-2 bg-zinc-950 hover:bg-zinc-800 text-zinc-200 font-medium rounded-xl text-center border border-zinc-800 hover:border-cyan-500/50 transition flex items-center justify-center space-x-1 shadow-sm">
                <span>📄</span>
                <span class="truncate">Resume</span>
              </a>
              <a id="pdf-cl-link" href="#" target="_blank" class="py-2.5 px-2 bg-zinc-950 hover:bg-zinc-800 text-zinc-200 font-medium rounded-xl text-center border border-zinc-800 hover:border-cyan-500/50 transition flex items-center justify-center space-x-1 shadow-sm">
                <span>✉️</span>
                <span class="truncate">Cover Letter</span>
              </a>
              <a id="pdf-combined-link" href="#" target="_blank" class="py-2.5 px-2 bg-zinc-950 hover:bg-zinc-800 text-cyan-300 font-medium rounded-xl text-center border border-cyan-500/40 hover:border-cyan-400 transition flex items-center justify-center space-x-1 shadow-sm">
                <span>📑</span>
                <span class="truncate">Combined</span>
              </a>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3 pt-1">
            <button id="job-btn-approve" onclick="resolveJob(true)" class="w-full py-3 px-4 bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-semibold rounded-xl text-sm transition shadow-lg shadow-emerald-950/40">
              ✅ Approve & Open
            </button>
            <button id="job-btn-skip" onclick="resolveJob(false)" class="w-full py-3 px-4 bg-zinc-800 hover:bg-rose-950/40 hover:text-rose-400 active:scale-95 text-zinc-400 font-medium rounded-xl text-sm transition border border-zinc-700">
              ✕ Skip Job
            </button>
          </div>
          <p id="job-tip" class="text-center text-xs text-zinc-500 hidden md:block">Tip: You can also use Orion's voice command to approve or skip.</p>
        </div>
      </section>

      <!-- CARD 2: AI JOB SEARCH PIPELINE (HEADLESS / NO TERMINAL) -->
      <section class="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-5 shadow-lg space-y-4">
        <div class="flex items-center justify-between pb-3 border-b border-zinc-800/80">
          <div class="flex items-center space-x-2">
            <span class="text-lg">🚀</span>
            <h2 class="text-sm font-semibold tracking-wider text-zinc-300 uppercase">AI Job Search Pipeline</h2>
          </div>
          <span id="pipeline-status-badge" class="text-xs px-2.5 py-0.5 rounded-full bg-zinc-800 text-zinc-400">● Idle</span>
        </div>

        <!-- Mode Toggle -->
        <div class="grid grid-cols-2 p-1 bg-zinc-950 border border-zinc-800 rounded-xl text-xs font-medium">
          <button id="tab-scrape" onclick="switchJobMode('scrape')" class="py-2 rounded-lg bg-zinc-800 text-white font-semibold transition">
            🌐 Auto-Scrape (GitHub)
          </button>
          <button id="tab-manual" onclick="switchJobMode('manual')" class="py-2 rounded-lg text-zinc-400 hover:text-zinc-200 transition">
            🔗 Manual URL
          </button>
        </div>

        <!-- Mode: Auto-Scrape -->
        <div id="pane-scrape" class="space-y-3">
          <p class="text-xs text-zinc-400 leading-relaxed">
            Scrapes fresh unapplied software postings from GitHub, drafts tailored CV & Cover Letters in the background, and queues them above for review.
          </p>
          <button onclick="startPipeline('scrape')" class="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 active:scale-95 text-white font-semibold rounded-xl text-sm transition shadow-lg shadow-cyan-950/30">
            Launch Auto-Scrape Session
          </button>
        </div>

        <!-- Mode: Manual URL -->
        <div id="pane-manual" class="hidden space-y-3">
          <input id="input-job-url" type="url" placeholder="Job Posting URL (LinkedIn, Greenhouse, etc.)..." class="w-full px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-xl text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-cyan-500">
          <div class="grid grid-cols-2 gap-2">
            <input id="input-job-comp" type="text" placeholder="Company (optional)" class="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-cyan-500">
            <input id="input-job-title" type="text" placeholder="Role Title (optional)" class="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-cyan-500">
          </div>
          <button onclick="startPipeline('manual')" class="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 active:scale-95 text-white font-semibold rounded-xl text-sm transition">
            Tailor Application for URL
          </button>
        </div>

        <!-- Live Progress Status Display -->
        <div id="pipeline-progress-box" class="hidden bg-zinc-950 border border-zinc-800 rounded-xl p-3.5 space-y-2">
          <div class="flex items-center justify-between text-xs">
            <span id="pipeline-progress-text" class="text-zinc-300 font-medium truncate">Processing...</span>
            <span id="pipeline-progress-num" class="font-mono text-cyan-400 text-[11px]"></span>
          </div>
          <div id="pipeline-current-job" class="text-xs text-zinc-400 font-mono truncate"></div>
          <button id="btn-pipeline-stop" onclick="stopPipeline()" class="w-full py-1 text-xs text-rose-400 hover:text-rose-300 border border-rose-950/60 bg-rose-950/20 rounded-lg transition mt-1">
            ⏹ Stop Background Pipeline
          </button>
        </div>
      </section>

      <!-- CARD 3: QUICK WEB SEARCH -->
      <section class="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-5 shadow-lg space-y-4">
        <div class="flex items-center space-x-2 pb-3 border-b border-zinc-800/80">
          <span class="text-lg">🔍</span>
          <h2 class="text-sm font-semibold tracking-wider text-zinc-300 uppercase">Orion Quick Search</h2>
        </div>

        <div class="flex space-x-2">
          <input id="search-query" type="text" placeholder="Ask Orion or search the live web..." onkeydown="if(event.key==='Enter') executeSearch()" class="flex-1 px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-xl text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-cyan-500">
          <button onclick="executeSearch()" class="px-5 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-white font-semibold rounded-xl text-sm transition">
            Search
          </button>
        </div>

        <div id="search-result" class="hidden text-xs bg-zinc-950/80 border border-zinc-800/80 rounded-xl p-3.5 max-h-56 overflow-y-auto custom-scroll text-zinc-300 whitespace-pre-wrap leading-relaxed"></div>
      </section>

    </div>

    <!-- RIGHT COLUMN (5 Cols on Desktop): Stock Intelligence & Local LLM Status -->
    <div class="md:col-span-5 flex flex-col space-y-6">

      <!-- CARD 4: STOCK INTELLIGENCE -->
      <section class="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-5 shadow-lg space-y-4">
        <div class="flex items-center justify-between pb-3 border-b border-zinc-800/80">
          <div class="flex items-center space-x-2">
            <span class="text-lg">📈</span>
            <h2 class="text-sm font-semibold tracking-wider text-zinc-300 uppercase">Stock Intelligence</h2>
          </div>
          <span class="text-[10px] text-zinc-400 font-mono">Auto connect-llm</span>
        </div>

        <div id="stock-recent-pills" class="flex flex-wrap gap-1.5 text-xs hidden"></div>

        <div class="flex space-x-2">
          <input id="stock-ticker" type="text" placeholder="Ticker (e.g. NVDA, AAPL)" uppercase onkeydown="if(event.key==='Enter') executeStock()" class="flex-1 px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-xl text-sm font-mono uppercase text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-cyan-500">
          <button onclick="executeStock()" class="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold rounded-xl text-sm transition shadow-lg shadow-cyan-950/30">
            Analyze
          </button>
        </div>

        <!-- Stock Loading Spinner -->
        <div id="stock-loading" class="hidden py-6 text-center space-y-2">
          <div class="w-6 h-6 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p class="text-xs text-zinc-400 font-mono">Connecting local-LLM & evaluating...</p>
        </div>

        <!-- Stock Result Display -->
        <div id="stock-result-card" class="hidden space-y-3">
          <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-4 space-y-2">
            <div class="flex items-center justify-between">
              <span id="res-ticker" class="text-xl font-bold font-mono text-white">NVDA</span>
              <span id="res-stance-badge" class="px-2.5 py-1 text-xs font-bold rounded-lg uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">BULLISH</span>
            </div>
            <div class="flex items-baseline space-x-2">
              <span id="res-price" class="text-2xl font-bold text-white">$124.50</span>
              <span id="res-range" class="text-xs text-zinc-400 font-mono">2-Wk: $115.00 - $128.00</span>
            </div>
            <div id="res-news-call" class="text-xs text-zinc-400 border-t border-zinc-800/80 pt-2 mt-2">
              Local LLM News Stance: Neutral
            </div>
          </div>

          <!-- Candlestick Chart Display -->
          <div id="chart-container" class="bg-zinc-950 border border-zinc-800 rounded-xl p-3 space-y-2 hidden">
            <div class="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider flex items-center justify-between">
              <span>📊 14-Day Candlestick Action</span>
              <span class="text-[10px] text-cyan-400 font-mono">Synced</span>
            </div>
            <img id="res-chart" src="" alt="Candlestick Chart" class="w-full rounded-lg border border-zinc-800 bg-zinc-900/60 object-contain">
          </div>

          <!-- Full Raw Analysis Toggle -->
          <details class="text-xs bg-zinc-950/50 border border-zinc-800 rounded-xl p-3">
            <summary class="cursor-pointer font-medium text-zinc-400 hover:text-zinc-200">View Full Quantitative Breakdown</summary>
            <div id="res-full-analysis" class="mt-2 text-zinc-400 whitespace-pre-wrap font-mono text-[11px] max-h-60 overflow-y-auto custom-scroll pt-2 border-t border-zinc-800"></div>
          </details>

          <a href="http://localhost:8000" target="_blank" class="block text-center py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl text-xs transition">
            Open Full Desktop Dashboard (Port 8000) ↗
          </a>
        </div>
      </section>

      <!-- SYSTEM STATUS FOOTER CARD -->
      <section class="bg-zinc-900/60 border border-zinc-800/80 rounded-2xl p-4 text-xs text-zinc-400 space-y-2">
        <div class="font-semibold uppercase tracking-wider text-[11px] text-zinc-500">System Link</div>
        <div class="flex items-center justify-between">
          <span>Tailscale Address:</span>
          <span class="font-mono text-zinc-300">__TAILSCALE_ADDR__</span>
        </div>
        <div class="flex items-center justify-between">
          <span>Local LLM Remote:</span>
          <span class="font-mono text-emerald-400">__REMOTE_LLM_HOST__</span>
        </div>
      </section>

    </div>

  </main>

  <script>
    // Token extraction & storage
    const urlParams = new URLSearchParams(window.location.search);
    let token = urlParams.get('token') || localStorage.getItem('orion_token') || '';
    if (urlParams.get('token')) {
      localStorage.setItem('orion_token', urlParams.get('token'));
      const cleanUrl = window.location.protocol + "//" + window.location.host + window.location.pathname;
      window.history.replaceState({}, document.title, cleanUrl);
    }

    if (!token) {
      setTimeout(() => {
        const input = prompt("🔐 Orion Dashboard Authentication\nPlease enter your token:");
        if (input && input.trim()) {
          localStorage.setItem('orion_token', input.trim());
          token = input.trim();
          window.location.reload();
        }
      }, 300);
    }

    function authHeader() {
      return token ? { 'Authorization': 'Bearer ' + token } : {};
    }

    // Auto layout badge indicator
    function updateDeviceBadge() {
      const badge = document.getElementById('device-badge');
      if (window.innerWidth >= 768) {
        badge.innerText = '🖥️ Desktop Command View';
      } else {
        badge.innerText = '📱 Mobile Touch View';
      }
    }
    window.addEventListener('resize', updateDeviceBadge);
    updateDeviceBadge();


    // Mode switch for Job Search
    let currentJobMode = 'scrape';
    function switchJobMode(mode) {
      currentJobMode = mode;
      const tabScrape = document.getElementById('tab-scrape');
      const tabManual = document.getElementById('tab-manual');
      const paneScrape = document.getElementById('pane-scrape');
      const paneManual = document.getElementById('pane-manual');

      if (mode === 'scrape') {
        tabScrape.className = 'py-2 rounded-lg bg-zinc-800 text-white font-semibold transition';
        tabManual.className = 'py-2 rounded-lg text-zinc-400 hover:text-zinc-200 transition';
        paneScrape.classList.remove('hidden');
        paneManual.classList.add('hidden');
      } else {
        tabManual.className = 'py-2 rounded-lg bg-zinc-800 text-white font-semibold transition';
        tabScrape.className = 'py-2 rounded-lg text-zinc-400 hover:text-zinc-200 transition';
        paneManual.classList.remove('hidden');
        paneScrape.classList.add('hidden');
      }
    }

    // Launch Background Pipeline (No Terminal)
    async function startPipeline(mode) {
      let payload = { mode: mode };
      if (mode === 'manual') {
        const url = document.getElementById('input-job-url').value.trim();
        if (!url) {
          alert('Please enter a job posting URL.');
          return;
        }
        payload.url = url;
        payload.company = document.getElementById('input-job-comp').value.trim();
        payload.title = document.getElementById('input-job-title').value.trim();
      }

      try {
        const res = await fetch('/api/job/start', {
          method: 'POST',
          headers: { ...authHeader(), 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const d = await res.json();
        pollPipelineStatus();
      } catch (err) {
        alert("Failed to start pipeline: " + err);
      }
    }

    // Stop Background Pipeline
    async function stopPipeline() {
      try {
        await fetch('/api/job/stop', { method: 'POST', headers: authHeader() });
        pollPipelineStatus();
      } catch (err) {}
    }

    // Poll Pipeline Status
    async function pollPipelineStatus() {
      try {
        const res = await fetch('/api/job/status', { headers: authHeader() });
        const d = await res.json();
        const badge = document.getElementById('pipeline-status-badge');
        const box = document.getElementById('pipeline-progress-box');
        const textEl = document.getElementById('pipeline-progress-text');
        const numEl = document.getElementById('pipeline-progress-num');
        const jobEl = document.getElementById('pipeline-current-job');
        const stopBtn = document.getElementById('btn-pipeline-stop');

        if (d && d.running) {
          badge.innerText = '● Running';
          badge.className = 'text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 animate-pulse font-medium';
          box.classList.remove('hidden');
          textEl.innerText = d.status_text || 'Working...';
          numEl.innerText = d.progress || '';
          jobEl.innerText = d.current_job || '';
          if (stopBtn) stopBtn.classList.remove('hidden');
        } else {
          badge.innerText = '● Idle';
          badge.className = 'text-xs px-2.5 py-0.5 rounded-full bg-zinc-800 text-zinc-400';
          if (d && d.status_text && d.status_text !== 'Idle') {
            box.classList.remove('hidden');
            textEl.innerText = d.status_text;
            numEl.innerText = '';
            jobEl.innerText = '';
            if (stopBtn) stopBtn.classList.add('hidden');
          } else {
            box.classList.add('hidden');
          }
        }
      } catch (err) {}
    }

    // Polling Job Bridge
    async function pollJobBridge() {
      try {
        const res = await fetch('/api/job/pending', { headers: authHeader() });
        if (res.status === 401) {
          document.getElementById('bridge-status-pill').innerText = '🔒 Auth Required';
          return;
        }
        const data = await res.json();
        const pill = document.getElementById('bridge-status-pill');
        const emptyState = document.getElementById('job-empty-state');
        const pendingState = document.getElementById('job-pending-state');

        if (data && data.pending && data.job) {
          const isScreening = (data.job.stage === 'screen');

          if (isScreening) {
            pill.innerText = '● Inspect URL';
            pill.className = 'text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 font-semibold';
            document.getElementById('job-card-header').className = 'bg-cyan-500/10 border border-cyan-500/20 rounded-xl p-3.5 transition-colors';
            document.getElementById('job-stage-badge').innerText = '🔍 Step 1: Inspect URL & Posting';
            document.getElementById('job-stage-badge').className = 'text-xs font-mono uppercase tracking-wider text-cyan-400 font-semibold';
            document.getElementById('job-pdf-docs').classList.add('hidden');
            document.getElementById('job-btn-approve').innerText = '⚡ Scrape & Tailor Application';
            document.getElementById('job-btn-skip').innerText = '✕ Skip Posting';
            document.getElementById('job-tip').innerText = 'Click "Open Job Posting ↗" above to check requirements before tailoring.';
          } else {
            pill.innerText = '● Pending Approval';
            pill.className = 'text-xs px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 font-semibold';
            document.getElementById('job-card-header').className = 'bg-amber-500/10 border border-amber-500/20 rounded-xl p-3.5 transition-colors';
            document.getElementById('job-stage-badge').innerText = '📄 Step 2: Review Generated Application';
            document.getElementById('job-stage-badge').className = 'text-xs font-mono uppercase tracking-wider text-amber-400 font-semibold';
            document.getElementById('job-pdf-docs').classList.remove('hidden');
            document.getElementById('job-btn-approve').innerText = '✅ Approve & Open';
            document.getElementById('job-btn-skip').innerText = '✕ Skip Job';
            document.getElementById('job-tip').innerText = "Tip: You can preview the PDFs above, or use Orion's voice command to approve/skip.";

            // Update PDF download links
            const tParam = token ? `&token=${encodeURIComponent(token)}` : '';
            const comp = data.job.company || 'Application';
            const cvFile = data.job.cv_pdf || `${comp}_Resume.pdf`;
            const clFile = data.job.cl_pdf || `${comp}_Cover_Letter.pdf`;
            const combFile = data.job.combined_pdf || `${comp}_Combined_Application.pdf`;

            document.getElementById('pdf-resume-link').href = `/api/job/pdf?file=${encodeURIComponent(cvFile)}${tParam}`;
            document.getElementById('pdf-cl-link').href = `/api/job/pdf?file=${encodeURIComponent(clFile)}${tParam}`;
            document.getElementById('pdf-combined-link').href = `/api/job/pdf?file=${encodeURIComponent(combFile)}${tParam}`;
          }

          emptyState.classList.add('hidden');
          pendingState.classList.remove('hidden');

          document.getElementById('job-title').innerText = data.job.title || 'Unknown Role';
          document.getElementById('job-company').innerText = data.job.company || 'Unknown Company';
          const link = document.getElementById('job-link');
          link.href = data.job.apply_url || '#';
        } else {
          pill.innerText = '● Idle';
          pill.className = 'text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400';
          emptyState.classList.remove('hidden');
          pendingState.classList.add('hidden');
        }
      } catch (err) {
        console.error("Poll error:", err);
      }
    }

    // Resolve Job (Approve / Skip)
    async function resolveJob(approved) {
      try {
        const res = await fetch('/api/job/resolve', {
          method: 'POST',
          headers: { ...authHeader(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ approved })
        });
        const out = await res.json();
        pollJobBridge();
      } catch (err) {
        alert("Action failed: " + err);
      }
    }


    // Render Stock Card (Data + Graphical Candlestick Chart)
    function renderStockCard(data) {
      if (!data) return;
      const card = document.getElementById('stock-result-card');
      card.classList.remove('hidden');

      const symbol = data.symbol || '';
      document.getElementById('res-ticker').innerText = symbol;
      const badge = document.getElementById('res-stance-badge');

      if (data.price !== null && data.price !== undefined) {
        document.getElementById('res-price').innerText = '$' + Number(data.price).toFixed(2);
        document.getElementById('res-range').innerText = data.range ? '2-Wk: ' + data.range : '';
        const stance = (data.stance || 'NEUTRAL').toUpperCase();
        badge.innerText = stance;
        if (stance.includes('BULL') || stance.includes('BUY') || stance.includes('UP')) {
          badge.className = 'px-2.5 py-1 text-xs font-bold rounded-lg uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
        } else if (stance.includes('BEAR') || stance.includes('SELL') || stance.includes('DOWN')) {
          badge.className = 'px-2.5 py-1 text-xs font-bold rounded-lg uppercase tracking-wider bg-rose-500/20 text-rose-400 border border-rose-500/30';
        } else {
          badge.className = 'px-2.5 py-1 text-xs font-bold rounded-lg uppercase tracking-wider bg-amber-500/20 text-amber-400 border border-amber-500/30';
        }
        document.getElementById('res-news-call').innerText = 'Local News Call: ' + (data.news_call || 'Neutral / None');

        // Graphical Candlestick Chart Display
        const chartBox = document.getElementById('chart-container');
        const chartImg = document.getElementById('res-chart');
        if (data.chart_url) {
          const tParam = token ? '&token=' + encodeURIComponent(token) : '';
          chartImg.src = data.chart_url + tParam + '&t=' + (data.timestamp || Date.now());
          chartBox.classList.remove('hidden');
        } else {
          chartBox.classList.add('hidden');
        }
      } else {
        document.getElementById('res-price').innerText = 'Symbol Not Found';
        document.getElementById('res-range').innerText = 'Check ticker spelling';
        badge.innerText = 'INVALID';
        badge.className = 'px-2.5 py-1 text-xs font-bold rounded-lg uppercase tracking-wider bg-zinc-800 text-zinc-400 border border-zinc-700';
        document.getElementById('res-news-call').innerText = data.raw_analysis || 'No trading data found on Yahoo Finance.';
        document.getElementById('chart-container').classList.add('hidden');
      }

      document.getElementById('res-full-analysis').innerText = data.raw_analysis || data.message || 'No breakdown available.';
    }

    // Execute Stock Analysis
    async function executeStock(customTicker) {
      const ticker = (customTicker || document.getElementById('stock-ticker').value).trim().toUpperCase();
      if (!ticker) return;
      document.getElementById('stock-ticker').value = ticker;

      const loader = document.getElementById('stock-loading');
      const card = document.getElementById('stock-result-card');
      loader.classList.remove('hidden');
      card.classList.add('hidden');

      try {
        const res = await fetch('/api/stock?symbol=' + encodeURIComponent(ticker), { headers: authHeader() });
        const data = await res.json();
        loader.classList.add('hidden');
        renderStockCard(data);

        // Persist to localStorage across page reload
        localStorage.setItem('orion_stock_cache', JSON.stringify({ ...data, timestamp: Date.now() }));
        loadStockHistory();
      } catch (err) {
        loader.classList.add('hidden');
        alert("Stock query failed: " + err);
      }
    }

    // Load Stock History Pills
    async function loadStockHistory() {
      try {
        const res = await fetch('/api/stock/history', { headers: authHeader() });
        const items = await res.json();
        const pillsContainer = document.getElementById('stock-recent-pills');
        if (!items || items.length === 0) {
          pillsContainer.classList.add('hidden');
          return;
        }
        pillsContainer.innerHTML = '<span class="text-zinc-500 text-[11px] self-center mr-1">Recent:</span>';
        items.forEach(item => {
          const btn = document.createElement('button');
          btn.className = 'px-2 py-0.5 rounded bg-zinc-950 border border-zinc-800 hover:border-cyan-500/50 text-zinc-300 font-mono text-[11px] transition';
          btn.innerText = item.symbol;
          btn.onclick = () => {
            document.getElementById('stock-ticker').value = item.symbol;
            renderStockCard(item);
            localStorage.setItem('orion_stock_cache', JSON.stringify({ ...item, timestamp: Date.now() }));
          };
          pillsContainer.appendChild(btn);
        });
        pillsContainer.classList.remove('hidden');

        // If no cached stock in localStorage, load first recent stock
        if (!localStorage.getItem('orion_stock_cache') && items.length > 0) {
          document.getElementById('stock-ticker').value = items[0].symbol;
          renderStockCard(items[0]);
          localStorage.setItem('orion_stock_cache', JSON.stringify({ ...items[0], timestamp: Date.now() }));
        }
      } catch (e) {}
    }

    // Execute Web Search
    async function executeSearch() {
      const q = document.getElementById('search-query').value.trim();
      if (!q) return;

      const out = document.getElementById('search-result');
      out.classList.remove('hidden');
      out.innerText = 'Searching web & summarizing...';

      try {
        const res = await fetch('/api/search?q=' + encodeURIComponent(q), { headers: authHeader() });
        const data = await res.json();
        out.innerText = data.result || 'No summary returned.';
        localStorage.setItem('orion_last_search', JSON.stringify({ q, result: data.result }));
      } catch (err) {
        out.innerText = 'Error performing search: ' + err;
      }
    }

    // Restore cached stock and search on reload
    try {
      const cached = localStorage.getItem('orion_stock_cache');
      if (cached) {
        const d = JSON.parse(cached);
        if (d.symbol) {
          document.getElementById('stock-ticker').value = d.symbol;
          renderStockCard(d);
        }
      }
    } catch (e) {}

    try {
      const cachedS = localStorage.getItem('orion_last_search');
      if (cachedS) {
        const s = JSON.parse(cachedS);
        if (s.q && s.result) {
          document.getElementById('search-query').value = s.q;
          const out = document.getElementById('search-result');
          out.innerText = s.result;
          out.classList.remove('hidden');
        }
      }
    } catch (e) {}

    loadStockHistory();
    pollPipelineStatus();

    function refreshAll() {
      pollJobBridge();
      pollPipelineStatus();
    }

    // Keyboard shortcuts for Desktop view
    window.addEventListener('keydown', (e) => {
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
      if (e.key === 'y' || e.key === 'Y') {
        const pending = !document.getElementById('job-pending-state').classList.contains('hidden');
        if (pending) resolveJob(true);
      } else if (e.key === 'n' || e.key === 'N') {
        const pending = !document.getElementById('job-pending-state').classList.contains('hidden');
        if (pending) resolveJob(false);
      }
    });

    // Start background poll every 2.5s
    setInterval(() => {
      pollJobBridge();
      pollPipelineStatus();
    }, 2500);
    pollJobBridge();
    pollPipelineStatus();
  </script>
</body>
</html>
"""


class DashboardRequestHandler(BaseHTTPRequestHandler):

    def _check_auth(self) -> bool:
        """Validates token strictly from Authorization header or URL query parameters."""
        # 1. Check Authorization: Bearer <token>
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            client_token = auth.split("Bearer ", 1)[1].strip()
            if secrets.compare_digest(client_token, AUTH_TOKEN):
                return True

        # 2. Check query parameter ?token=<token>
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if "token" in qs and secrets.compare_digest(qs["token"][0], AUTH_TOKEN):
            return True

        return False

    def _send_cors_headers(self):
        origin = self.headers.get("Origin", "")
        host = self.headers.get("Host", "")
        if origin and host and host in origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def _render_html(self) -> bytes:
        tailscale_display = f"{TAILSCALE_IP}:{PORT}" if TAILSCALE_IP else "Not configured"
        remote_llm_display = f"{REMOTE_LLM_HOST} (Linked)" if REMOTE_LLM_HOST else "Disabled"
        rendered_html = (
            HTML_TEMPLATE
            .replace("__TAILSCALE_ADDR__", tailscale_display)
            .replace("__REMOTE_LLM_HOST__", remote_llm_display)
        )
        return rendered_html.encode("utf-8")

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ["/", "/index.html"]:
            html_bytes = self._render_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_bytes)))
            self.end_headers()
        else:
            self.send_response(200)
            self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        # Serve Dashboard Root HTML (zero token leakage)
        if path in ["/", "/index.html"]:
            html_bytes = self._render_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_bytes)))
            self.end_headers()
            self.wfile.write(html_bytes)
            return

        # Security check for all API endpoints
        if not self._check_auth():
            self._send_json({"error": "Unauthorized. Invalid or missing token."}, status=401)
            return

        # API: Check Pending Job Bridge
        if path == "/api/job/pending":
            pending = bridge.get_pending_job()
            if pending:
                self._send_json({"pending": True, "job": pending})
            else:
                self._send_json({"pending": False})
            return

        # API: Query Headless Job Search Pipeline Status
        if path == "/api/job/status":
            status_file = Path.home() / ".orion_job_status.json"
            if status_file.exists():
                try:
                    data = json.loads(status_file.read_text(encoding="utf-8"))
                    pid = data.get("pid")
                    if pid and data.get("running"):
                        try:
                            with open(f"/proc/{pid}/status", "r") as pf:
                                if "State:\tZ" in pf.read():
                                    data["running"] = False
                                    data["status_text"] = "Pipeline completed."
                        except OSError:
                            data["running"] = False
                            data["status_text"] = "Pipeline completed."
                    self._send_json(data)
                    return
                except Exception:
                    pass
            self._send_json({"running": False, "status_text": "Idle"})
            return

        # API: Serve / Download Generated Job Application PDFs
        if path == "/api/job/pdf":
            req_file = qs.get("file", [""])[0].strip()
            if not req_file:
                self._send_json({"error": "Missing file parameter"}, status=400)
                return

            clean_name = Path(req_file).name
            if not clean_name.endswith(".pdf"):
                clean_name += ".pdf"

            pdf_dir = Path("/home/grim/Downloads/ai_job_search/ai_job_search/output").resolve()
            target_pdf = (pdf_dir / clean_name).resolve()

            if not target_pdf.is_relative_to(pdf_dir) or not target_pdf.is_file():
                self._send_json({"error": f"PDF not found: {clean_name}"}, status=404)
                return

            try:
                pdf_bytes = target_pdf.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Length", str(len(pdf_bytes)))
                self.send_header("Content-Disposition", f'inline; filename="{clean_name}"')
                self.send_header("Cache-Control", "public, max-age=600")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(pdf_bytes)
                return
            except Exception as e:
                self._send_json({"error": f"Error reading PDF: {e}"}, status=500)
                return

        # API: Proxy Stock Chart Image
        if path == "/api/stock/chart":
            ticker = qs.get("ticker", [""])[0].strip().upper()
            if not ticker or not re.match(r"^[A-Z0-9.-]{1,10}$", ticker):
                self._send_json({"error": "Invalid ticker"}, status=400)
                return
            try:
                chart_url = f"http://localhost:8000/charts/{ticker}_chart.png"
                req = urllib.request.Request(chart_url)
                with urllib.request.urlopen(req, timeout=5) as res:
                    img_bytes = res.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(img_bytes)))
                    self.send_header("Cache-Control", "public, max-age=300")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(img_bytes)
                    return
            except Exception as e:
                self._send_json({"error": f"Chart not found: {e}"}, status=404)
                return

        # API: Query Recent Stock History
        if path == "/api/stock/history":
            try:
                req = urllib.request.Request("http://localhost:8000/api/history")
                with urllib.request.urlopen(req, timeout=3) as res:
                    raw_hist = json.loads(res.read().decode("utf-8"))
                hist = []
                for item in raw_hist[:6]:
                    t = item.get("ticker")
                    if not t:
                        continue
                    an = item.get("analysis") or ""
                    is_bull = "BULLISH" in an
                    is_bear = "BEARISH" in an
                    st = "BULLISH" if is_bull else "BEARISH" if is_bear else "NEUTRAL"
                    low = item.get("two_week_low")
                    high = item.get("two_week_high")
                    rng = f"${low:.2f} - ${high:.2f}" if low is not None and high is not None else ""
                    hist.append({
                        "symbol": t,
                        "price": item.get("current_price"),
                        "stance": st,
                        "range": rng,
                        "news_call": item.get("news_summary") or "",
                        "raw_analysis": an,
                        "chart_url": f"/api/stock/chart?ticker={t}"
                    })
                self._send_json(hist)
            except Exception:
                self._send_json([])
            return

        # API: Query Stock Analysis
        if path == "/api/stock":
            symbol = qs.get("symbol", [""])[0].strip().upper()
            symbol = {"APPL": "AAPL", "FB": "META"}.get(symbol, symbol)
            if not symbol or not re.match(r"^[A-Z0-9.-]{1,10}$", symbol):
                self._send_json({"error": "Invalid ticker symbol"}, status=400)
                return

            try:
                ensure_llm_connected()
                req = urllib.request.Request(f"http://localhost:8000/analyze/{symbol}")
                try:
                    with urllib.request.urlopen(req, timeout=60) as res:
                        data = json.loads(res.read().decode("utf-8"))
                except urllib.error.HTTPError as he:
                    self._send_json({
                        "symbol": symbol,
                        "price": None,
                        "stance": "INVALID",
                        "raw_analysis": f"Ticker '{symbol}' was not found or has no active trading data on Yahoo Finance."
                    })
                    return

                analysis_str = data.get("analysis", "")
                price = data.get("current_price")
                low = data.get("two_week_low")
                high = data.get("two_week_high")
                rng = f"${low:.2f} - ${high:.2f}" if low is not None and high is not None else ""
                local_summary = (data.get("news_summary") or "").strip()

                m_stance = re.search(r"Final Operational Stance:\s*\*?([^\n*]+)", analysis_str)
                if not m_stance:
                    m_stance = re.search(r"FINAL OPERATIONAL VERDICT:\s*([^\n]+)", analysis_str)
                stance = m_stance.group(1).strip() if m_stance else "NEUTRAL"

                self._send_json({
                    "symbol": symbol,
                    "stance": stance,
                    "price": price,
                    "range": rng,
                    "news_call": local_summary or "Neutral / None",
                    "raw_analysis": analysis_str,
                    "chart_url": f"/api/stock/chart?ticker={symbol}"
                })
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        # API: Web Search
        if path == "/api/search":
            q = qs.get("q", [""])[0].strip()
            if not q:
                self._send_json({"error": "Empty search query"}, status=400)
                return

            # Instant zero-token live weather check
            clean_q = q.strip().rstrip("?.! ")
            city = None
            for pat in [
                r"(?:weather\s+(?:in|for|at|like in)?\s*|what(?:'s| is| how's| how is)\s+(?:the\s+)?weather\s+(?:in|for|at|like in)?\s*)(.+)",
                r"(.+?)\s+weather",
            ]:
                m = re.search(pat, clean_q, re.I)
                if m:
                    raw_city = m.group(1).strip()
                    cleaned = re.sub(r"\b(today|now|currently|right now|outside|this week|tomorrow|like)\b", "", raw_city, flags=re.I).strip("?.! ,")
                    if cleaned:
                        city = cleaned
                        break

            if city:
                try:
                    w_url = f"https://wttr.in/{urllib.parse.quote(city)}?format=%l:+%C,+%t+(Feels+like+%f),+Wind:+%w,+Humidity:+%h"
                    w_req = urllib.request.Request(w_url, headers={"User-Agent": "curl/8.0"})
                    with urllib.request.urlopen(w_req, timeout=4) as w_res:
                        w_text = w_res.read().decode("utf-8").strip()
                        if w_text and "Unknown location" not in w_text:
                            self._send_json({"query": q, "result": f"🌤️ Live Weather for {city.title()}:\n{w_text}"})
                            return
                except Exception:
                    pass

            try:
                results = _ddg_search(q, max_results=5)
                search_snippets = _format_ddg(q, results)
                if not search_snippets or not results:
                    self._send_json({"query": q, "result": f"No web results found for '{q}'."})
                    return

                from datetime import datetime
                today = datetime.now().strftime("%B %d, %Y")
                sys_prompt = (
                    f"You are a real-time web search summarizer. Today is {today}. "
                    "Summarize the answer clearly and concisely based STRICTLY on the search results. "
                    "DO NOT use <think> tags. Output only the concise answer."
                )
                user_prompt = f"User Query: {q}\n\nSearch Results:\n{search_snippets}\n\nConcise Answer:"
                ans = client.chat(user_prompt, system=sys_prompt, max_tokens=600)
                clean_ans = re.sub(r"<think>.*?</think>", "", ans, flags=re.DOTALL).strip()
                self._send_json({"query": q, "result": clean_ans or ans or search_snippets})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        self._send_json({"error": "Not Found"}, status=404)

    def do_POST(self):
        if not self._check_auth():
            self._send_json({"error": "Unauthorized"}, status=401)
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Read JSON body
        content_len = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_len > 0:
            try:
                body = json.loads(self.rfile.read(content_len).decode("utf-8"))
            except Exception:
                pass

        # API: Resolve Job Bridge (Approve / Skip)
        if path == "/api/job/resolve":
            approved = bool(body.get("approved", False))
            job = bridge.get_pending_job()

            if approved and job:
                # If in URL screening stage, just proceed with tailoring without opening desktop windows yet
                if job.get("stage") == "screen":
                    bridge.resolve_approval(True)
                    self._send_json({"status": "resolved", "approved": True, "message": "Proceeding to scrape and tailor application."})
                    return

                # If in final review stage, open posting and output folder on desktop
                apply_url = job.get("apply_url", "").strip()
                if not apply_url or apply_url == "N/A":
                    query = f"{job.get('company', '')} {job.get('title', '')} careers application"
                    apply_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"

                # 1. Open job posting on Desktop
                webbrowser.open(apply_url)

                # 2. Open PDF output directory on Desktop
                output_dir = os.path.abspath("/home/grim/Downloads/ai_job_search/ai_job_search/output")
                if os.path.exists(output_dir):
                    subprocess.Popen(["xdg-open", output_dir])

                bridge.resolve_approval(True)
                self._send_json({"status": "resolved", "approved": True, "message": "Job approved and opened on desktop."})
            else:
                bridge.resolve_approval(False)
                self._send_json({"status": "resolved", "approved": False, "message": "Job skipped."})
            return

        # API: Start Headless Job Search Pipeline (No Terminal)
        if path == "/api/job/start":
            mode = body.get("mode", "scrape")
            url = body.get("url", "").strip()
            company = body.get("company", "").strip()
            title = body.get("title", "").strip()

            python_bin = "/home/grim/Downloads/ai_job_search/.venv/bin/python"
            script_path = "/home/grim/Downloads/ai_job_search/ai_job_search/framework/headless.py"

            cmd = [python_bin, script_path, "--mode", mode]
            if mode == "manual" and url:
                cmd.extend(["--url", url])
                if company:
                    cmd.extend(["--company", company])
                if title:
                    cmd.extend(["--title", title])

            env = os.environ.copy()
            if API_KEYS_FILE.exists():
                try:
                    k_data = json.loads(API_KEYS_FILE.read_text(encoding="utf-8"))
                    if "gemini_api_key" in k_data:
                        env["GEMINI_API_KEY"] = k_data["gemini_api_key"]
                        env["GOOGLE_API_KEY"] = k_data["gemini_api_key"]
                    if "groq_api_key" in k_data:
                        env["GROQ_API_KEY"] = k_data["groq_api_key"]
                except Exception:
                    pass

            try:
                log_file = open("/home/grim/Downloads/ai_job_search/ai_job_search/headless.log", "a")
                proc = subprocess.Popen(
                    cmd,
                    cwd="/home/grim/Downloads/ai_job_search/ai_job_search",
                    env=env,
                    stdout=log_file,
                    stderr=log_file,
                    start_new_session=True
                )
                status_file = Path.home() / ".orion_job_status.json"
                status_file.write_text(json.dumps({
                    "running": True,
                    "status_text": "Starting background pipeline...",
                    "current_job": f"{company or 'Auto'} {title or ''}".strip(),
                    "progress": "Starting",
                    "pid": proc.pid,
                    "timestamp": time.time()
                }))
                self._send_json({"status": "started", "pid": proc.pid, "message": "Pipeline started in background."})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        # API: Stop Headless Job Search Pipeline
        if path == "/api/job/stop":
            status_file = Path.home() / ".orion_job_status.json"
            if status_file.exists():
                try:
                    data = json.loads(status_file.read_text(encoding="utf-8"))
                    pid = data.get("pid")
                    if pid:
                        try:
                            os.kill(pid, 15)
                        except OSError:
                            pass
                    data["running"] = False
                    data["status_text"] = "Pipeline stopped by user."
                    status_file.write_text(json.dumps(data))
                except Exception:
                    pass
            self._send_json({"status": "stopped"})
            return


        self._send_json({"error": "Not Found"}, status=404)

    def log_message(self, format, *args):
        # Keep stdout clean; only log errors or non-200 responses
        if len(args) >= 2 and str(args[1]) not in ["200", "304"]:
            sys.stderr.write(f"[Dashboard] {format % args}\n")


def run_server(host=None, port=None):
    host = host or os.getenv("DASHBOARD_HOST") or _config.get("dashboard_host") or "0.0.0.0"
    port = port or PORT
    server = ThreadingHTTPServer((host, port), DashboardRequestHandler)
    print("\n" + "=" * 60)
    print("🚀 ORION COMPANION DASHBOARD ONLINE")
    print("=" * 60)
    print(f"🖥️  Local URL:            http://127.0.0.1:{port}/?token={AUTH_TOKEN}")
    if TAILSCALE_IP:
        print(f"📱  Phone / Tailscale:    http://{TAILSCALE_IP}:{port}/?token={AUTH_TOKEN}")
    else:
        print("📱  Phone / Tailscale:    (Tailscale IP not configured or detected)")
    print("=" * 60)
    print("🔑 Token configured via config/api_keys.json or .env")
    print("✨ Automatically adapts between Desktop Command View & Mobile View\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🔴 Dashboard shutting down...")
        server.server_close()


if __name__ == "__main__":
    run_server()
