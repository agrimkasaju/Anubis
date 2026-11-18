"""
O.R.I.O.N On-Demand System Telemetry Provider.
Captures instantaneous CPU, memory, GPU, and thermal statistics without continuous background polling.
"""

from __future__ import annotations
import os
import subprocess
import time
import psutil


def _get_gpu_stats() -> dict[str, float | str]:
    """Retrieves GPU utilization, VRAM usage, and temperatures with short timeouts."""
    # Try NVIDIA
    try:
        r = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=0.6,
        )
        if r.returncode == 0 and r.stdout.strip():
            parts = [p.strip() for p in r.stdout.strip().split("\n")[0].split(",")]
            if len(parts) >= 4:
                return {
                    "available": True,
                    "type": "NVIDIA",
                    "util_pct": float(parts[0]),
                    "mem_used_mb": float(parts[1]),
                    "mem_total_mb": float(parts[2]),
                    "temp_c": float(parts[3]),
                }
    except Exception:
        pass

    # Try AMD DRM / sysfs
    try:
        busy_path = "/sys/class/drm/card0/device/gpu_busy_percent"
        if os.path.exists(busy_path):
            with open(busy_path, "r") as f:
                pct = float(f.read().strip())
                return {
                    "available": True,
                    "type": "AMD",
                    "util_pct": pct,
                    "mem_used_mb": 0.0,
                    "mem_total_mb": 0.0,
                    "temp_c": -1.0,
                }
    except Exception:
        pass

    return {
        "available": False,
        "type": "N/A",
        "util_pct": -1.0,
        "mem_used_mb": 0.0,
        "mem_total_mb": 0.0,
        "temp_c": -1.0,
    }


def _get_cpu_temp() -> float:
    """Extracts CPU package or core temperature in Celsius."""
    try:
        temps = psutil.sensors_temperatures()
        for key in ("k10temp", "coretemp", "cpu_thermal", "acpitz"):
            if key in temps and temps[key]:
                return float(temps[key][0].current)
    except Exception:
        pass
    return -1.0


def collect_system_vitals(focus: str = "all") -> dict:
    """
    Collects instantaneous snapshot of host hardware performance.
    Returns structured data and a speech-ready summary string.
    """
    cpu_pct = psutil.cpu_percent(interval=0.15)
    vm = psutil.virtual_memory()
    mem_pct = vm.percent
    mem_used_gb = vm.used / (1024**3)
    mem_total_gb = vm.total / (1024**3)

    gpu = _get_gpu_stats()
    cpu_temp = _get_cpu_temp()

    # Construct spoken response based on focus
    speech_parts = []
    if focus in ("all", "cpu"):
        speech_parts.append(f"CPU utilization is at {cpu_pct:.0f} percent")
        if cpu_temp > 0:
            speech_parts.append(f"running at {cpu_temp:.0f} degrees")

    if focus in ("all", "memory"):
        speech_parts.append(f"memory is at {mem_pct:.0f} percent, using {mem_used_gb:.1f} of {mem_total_gb:.0f} gigabytes")

    if focus in ("all", "gpu") and gpu["available"]:
        gpu_str = f"GPU load is at {gpu['util_pct']:.0f} percent"
        if gpu["temp_c"] > 0:
            gpu_str += f" at {gpu['temp_c']:.0f} degrees"
        speech_parts.append(gpu_str)

    if not speech_parts:
        speech_summary = f"All systems nominal. CPU is at {cpu_pct:.0f}%, RAM at {mem_pct:.0f}%."
    else:
        speech_summary = "All systems nominal. " + ", and ".join(speech_parts) + "."

    return {
        "speech_summary": speech_summary,
        "timestamp": time.time(),
        "focus": focus,
        "cpu": {
            "percent": cpu_pct,
            "temp_c": cpu_temp,
            "cores": psutil.cpu_count(logical=True),
        },
        "memory": {
            "percent": mem_pct,
            "used_gb": round(mem_used_gb, 2),
            "total_gb": round(mem_total_gb, 2),
        },
        "gpu": gpu,
    }
