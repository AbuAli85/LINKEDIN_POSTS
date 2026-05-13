"""SmartPro Hub data bridge — fetch live metrics and manage the job announcement queue."""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

SMARTPRO_API = os.environ.get("SMARTPRO_API_URL", "https://www.thesmartpro.io")
PENDING_JOBS_FILE = Path(__file__).parent / "smartpro_feed" / "pending_jobs.json"

# 5-minute in-memory cache
_metrics_cache: dict | None = None
_metrics_expires: float = 0.0


def fetch_metrics() -> dict | None:
    """Fetch aggregate platform metrics from SmartPro Hub. Cached for 5 minutes."""
    global _metrics_cache, _metrics_expires
    now = time.time()
    if _metrics_cache and now < _metrics_expires:
        return _metrics_cache

    try:
        resp = requests.get(f"{SMARTPRO_API}/api/public/metrics", timeout=10)
        resp.raise_for_status()
        _metrics_cache = resp.json()
        _metrics_expires = now + 300  # 5 min
        return _metrics_cache
    except Exception as e:
        print(f"[smartpro-bridge] fetch_metrics failed: {e}")
        return _metrics_cache  # return stale cache if available


def get_pending_jobs() -> list[dict]:
    """Return jobs that haven't been announced yet."""
    if not PENDING_JOBS_FILE.exists():
        return []
    try:
        jobs = json.loads(PENDING_JOBS_FILE.read_text(encoding="utf-8"))
        if not isinstance(jobs, list):
            return []
        return [j for j in jobs if not j.get("announced")]
    except Exception:
        return []


def mark_job_announced(job_id: int) -> None:
    """Mark a job as announced in pending_jobs.json."""
    if not PENDING_JOBS_FILE.exists():
        return
    try:
        jobs = json.loads(PENDING_JOBS_FILE.read_text(encoding="utf-8"))
        if not isinstance(jobs, list):
            return
        for j in jobs:
            if j.get("id") == job_id:
                j["announced"] = True
                j["announced_at"] = datetime.now(timezone.utc).isoformat()
        PENDING_JOBS_FILE.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[smartpro-bridge] mark_job_announced failed: {e}")


def build_metrics_context(metrics: dict | None) -> str:
    """Build a metrics context block to inject into generation prompts."""
    if not metrics:
        return ""
    p = metrics.get("platform", {})
    lines = [
        "SMARTPRO PLATFORM METRICS (live data — use for credibility and specificity):",
        f"- Active open jobs on the platform: {p.get('active_jobs', '?')}",
        f"- Companies actively hiring: {p.get('companies_hiring', '?')}",
        f"- Registered candidates: {p.get('candidates_registered', '?')}",
        f"- Applications submitted this week: {p.get('applications_this_week', '?')}",
        f"- Total applications processed: {p.get('applications_total', '?')}",
        f"- New jobs posted this week: {p.get('jobs_posted_this_week', '?')}",
    ]
    top_roles = metrics.get("top_roles", [])
    if top_roles:
        roles_str = ", ".join(r["title"] for r in top_roles[:3])
        lines.append(f"- Most in-demand roles right now: {roles_str}")
    top_locs = metrics.get("top_locations", [])
    if top_locs:
        locs_str = ", ".join(loc["location"] for loc in top_locs[:3] if loc.get("location"))
        if locs_str:
            lines.append(f"- Top hiring locations: {locs_str}")
    return "\n".join(lines) + "\n\n"
