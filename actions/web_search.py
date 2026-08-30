#web_search.py
import urllib.parse
import webbrowser
import json
import sys
from pathlib import Path

import re
from datetime import datetime

current_date = datetime.now().strftime("%B %Y")

system_prompt = (
    f"You are a web search summarizer. The current date is {current_date}. "
    "Do NOT claim dates in 2026 are in the future. Analyze the provided search results and summarize them directly. "
    "CRITICAL: DO NOT use <think> tags. Do not explain your reasoning. Output ONLY the final summary."
)

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _gemini_search(query: str) -> str:
    from google import genai

    client   = genai.Client(api_key=_get_api_key())
    response = client.models.generate_content(
        model=get_gemini_model(),
        contents=query,
        config={"tools": [{"google_search": {}}]},
    )

    text = ""
    for part in response.candidates[0].content.parts:
        if hasattr(part, "text") and part.text:
            text += part.text

    text = text.strip()
    if not text:
        raise ValueError("Gemini returned an empty response.")
    return text


def _ddg_search(query: str, max_results: int = 6) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title":   r.get("title",  ""),
                "snippet": r.get("body",   ""),
                "url":     r.get("href",   ""),
            })
    return results


def _format_ddg(query: str, results: list[dict]) -> str:
    if not results:
        return f"No results found for: {query}"

    lines = [f"Search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        if r.get("title"):   lines.append(f"{i}. {r['title']}")
        if r.get("snippet"): lines.append(f"   {r['snippet']}")
        if r.get("url"):     lines.append(f"   {r['url']}")
        lines.append("")
    return "\n".join(lines).strip()

def _compare(items: list[str], aspect: str) -> str:
    query = (
        f"Compare {', '.join(items)} in terms of {aspect}. "
        "Give specific facts and data."
    )
    try:
        return _gemini_search(query)
    except Exception as e:
        print(f"[WebSearch] ⚠️ Gemini compare failed: {e} — falling back to DDG")

    # DDG fallback: fetch results per item and merge
    all_results: dict[str, list] = {}
    for item in items:
        try:
            all_results[item] = _ddg_search(f"{item} {aspect}", max_results=3)
        except Exception:
            all_results[item] = []

    lines = [f"Comparison — {aspect.upper()}", "─" * 40]
    for item in items:
        lines.append(f"\n▸ {item}")
        for r in all_results.get(item, [])[:2]:
            if r.get("snippet"):
                lines.append(f"  • {r['snippet']}")
    return "\n".join(lines)

def web_search(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    query  = params.get("query", "").strip()
    mode   = params.get("mode",  "search").lower().strip()
    items  = params.get("items", [])
    aspect = params.get("aspect", "general").strip() or "general"

    if not query and not items:
        return "Please provide a search query, sir."

    if items and mode != "compare":
        mode = "compare"

    if player:
        player.write_log(f"[Search] {query or ', '.join(items)}")

    print(f"[WebSearch] 🔍 Query: {query!r}  Mode: {mode}")

    # 1. Open search visually in Vivaldi/browser
    try:
        search_url = f"https://duckduckgo.com/?q={urllib.parse.quote(query)}"
        import shutil
        import subprocess
        vivaldi_bin = shutil.which("vivaldi") or shutil.which("vivaldi-stable") or "/usr/bin/vivaldi"
        
        if vivaldi_bin and Path(vivaldi_bin).exists():
            subprocess.Popen([vivaldi_bin, search_url])
            print(f"[WebSearch] 🌐 Native subprocess spawned Vivaldi tab for: {query}")
        else:
            webbrowser.open_new_tab(search_url)
            print(f"[WebSearch] 🌐 Fallback browser tab opened for: {query}")
    except Exception as e:
        print(f"[WebSearch] ⚠️ Failed to open custom browser context: {e}")

    # 2. Scrape live DuckDuckGo results first
    search_snippets = ""
    try:
        results = _ddg_search(query, max_results=5)
        search_snippets = _format_ddg(query, results)
        print(f"[WebSearch] 📡 Scraped {len(results)} live search snippets.")
    except Exception as e:
        print(f"[WebSearch] ⚠️ DDG search failed: {e}")

    # 3. Summarize the actual search results with OpenRouter
    current_date_str = datetime.now().strftime("%B %d, %Y")
    system_prompt = (
        f"You are a real-time web search summarizer. Today's date is {current_date_str}. "
        "Summarize the answer clearly and concisely based STRICTLY on the provided search results. "
        "DO NOT use <think> tags. Output only the concise answer."
    )

    prompt = (
        f"User Query: {query}\n\n"
        f"Live Web Search Results:\n{search_snippets if search_snippets else 'No search snippets retrieved.'}\n\n"
        "Provide a concise summary answering the user query:"
    )

    try:
        from or_client import client
        result = client.chat(
            prompt,
            system=system_prompt
        )
        # Strip out any rogue <think>...</think> tags
        clean_result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()
        print("[WebSearch] ✅ Summarized live web search successfully.")
        return clean_result or result
    except Exception as e:
        print(f"[WebSearch] ⚠️ OpenRouter summarizer failed ({e}) — returning raw snippets...")
        return search_snippets or "Sir, I was unable to retrieve live web results at this moment."