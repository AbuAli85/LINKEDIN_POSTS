"""Lead enrichment for SmartPro outreach pipeline.

Combines two data sources:
  - Bright Data (Web Scraper API / Dataset API) — public LinkedIn profile data
  - Apollo.io People Match API — email, phone, title, company intel

Usage:
  # Enrich a single LinkedIn profile URL
  python enrich_leads.py one https://www.linkedin.com/in/fahad-alamri-smartpro/

  # Enrich a batch from a file (one URL per line)
  python enrich_leads.py batch prospects.txt

  # Dry run — show what would be written, do not modify leads.csv
  python enrich_leads.py one <url> --dry-run

Required env vars:
  BRIGHTDATA_API_KEY      — from your Bright Data dashboard
  BRIGHTDATA_LI_DATASET   — Bright Data dataset_id for the LinkedIn People dataset
                            (defaults to gd_l1viktl72bvl7bjuj0 — the public LI People dataset)
  APOLLO_API_KEY          — from https://app.apollo.io/#/settings/integrations/api

Optional:
  ENRICH_RATE_LIMIT_SECS  — pause between API calls in batch mode (default 1.5)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).parent
LEADS_CSV = ROOT / "leads.csv"
ENRICH_LOG_DIR = ROOT / "enrichment_history"
ENRICH_LOG_DIR.mkdir(exist_ok=True)

# Bright Data
BD_BASE = "https://api.brightdata.com/datasets/v3"
BD_DEFAULT_LI_DATASET = "gd_l1viktl72bvl7bjuj0"  # LinkedIn People dataset

# Apollo
APOLLO_BASE = "https://api.apollo.io/api/v1"

# CSV schema — MUST match the header in leads.csv
LEADS_CSV_FIELDS = [
    "name", "linkedin_url", "company", "title_guess", "intent",
    "post_topic", "comment_text", "reply_status", "dm_status",
    "first_seen", "last_touchpoint", "demo_requested", "demo_date",
    "demo_outcome", "deal_value", "notes",
]


# ---------------------------------------------------------------------------
# Bright Data — LinkedIn People dataset
# ---------------------------------------------------------------------------

def _bd_headers() -> dict:
    key = (os.environ.get("BRIGHTDATA_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "BRIGHTDATA_API_KEY not set. Get one from your Bright Data dashboard, "
            "then `export BRIGHTDATA_API_KEY=...`."
        )
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def bd_trigger_li_profile(linkedin_url: str) -> str:
    """Trigger a Bright Data scrape for one LinkedIn profile URL. Returns snapshot_id."""
    dataset_id = os.environ.get("BRIGHTDATA_LI_DATASET", BD_DEFAULT_LI_DATASET)
    resp = requests.post(
        f"{BD_BASE}/trigger",
        headers=_bd_headers(),
        params={"dataset_id": dataset_id, "include_errors": "true"},
        json=[{"url": linkedin_url}],
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    snapshot_id = body.get("snapshot_id") or body.get("collection_id")
    if not snapshot_id:
        raise RuntimeError(f"Bright Data trigger returned no snapshot_id: {body}")
    return snapshot_id


def bd_poll_snapshot(snapshot_id: str, max_wait: int = 180, interval: int = 5) -> list[dict]:
    """Poll snapshot until ready, then download. Returns list of profile dicts."""
    status_url = f"{BD_BASE}/progress/{snapshot_id}"
    deadline = time.time() + max_wait

    while time.time() < deadline:
        r = requests.get(status_url, headers=_bd_headers(), timeout=15)
        r.raise_for_status()
        status = r.json().get("status", "")
        if status == "ready":
            break
        if status == "failed":
            raise RuntimeError(f"Bright Data snapshot {snapshot_id} failed.")
        time.sleep(interval)
    else:
        raise TimeoutError(f"Bright Data snapshot {snapshot_id} not ready after {max_wait}s.")

    dl = requests.get(
        f"{BD_BASE}/snapshot/{snapshot_id}",
        headers=_bd_headers(),
        params={"format": "json"},
        timeout=60,
    )
    dl.raise_for_status()
    data = dl.json()
    return data if isinstance(data, list) else [data]


# ---------------------------------------------------------------------------
# Apollo — People Match
# ---------------------------------------------------------------------------

def _apollo_headers() -> dict:
    key = (os.environ.get("APOLLO_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "APOLLO_API_KEY not set. Get one at "
            "https://app.apollo.io/#/settings/integrations/api"
        )
    return {
        "X-Api-Key": key,
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }


def apollo_people_match(linkedin_url: str | None = None,
                        first_name: str | None = None,
                        last_name: str | None = None,
                        company: str | None = None) -> dict | None:
    """Look up a person via Apollo's People Match endpoint. Returns the person dict or None."""
    payload: dict[str, Any] = {"reveal_personal_emails": False}
    if linkedin_url:
        payload["linkedin_url"] = linkedin_url
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name
    if company:
        payload["organization_name"] = company

    resp = requests.post(
        f"{APOLLO_BASE}/people/match",
        headers=_apollo_headers(),
        json=payload,
        timeout=30,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json().get("person")


# ---------------------------------------------------------------------------
# Segment heuristic — matches outreach_tracker.py A/B/C definitions
# ---------------------------------------------------------------------------

SEG_A_KEYWORDS = ("hr", "people", "talent", "owner", "founder", "ceo", "operations", "manager")
SEG_B_KEYWORDS = ("invest", "minister", "government", "vision 2040", "policy", "fund", "vc", "board")
SEG_C_KEYWORDS = ("engineer", "developer", "saas", "cto", "tech", "build", "software", "platform")


def guess_segment(title: str = "", company: str = "", headline: str = "") -> str:
    blob = " ".join((title or "", company or "", headline or "")).lower()
    if any(k in blob for k in SEG_B_KEYWORDS):
        return "B"
    if any(k in blob for k in SEG_C_KEYWORDS):
        return "C"
    if any(k in blob for k in SEG_A_KEYWORDS):
        return "A"
    return ""  # unknown — let outreach_tracker default


# ---------------------------------------------------------------------------
# Merge + write to leads.csv
# ---------------------------------------------------------------------------

def merge_record(linkedin_url: str, bd_profile: dict | None, apollo_person: dict | None) -> dict:
    """Combine Bright Data + Apollo into one leads.csv row."""
    bd = bd_profile or {}
    ap = apollo_person or {}

    # Prefer Apollo for contact info (more reliable email/phone), BD for raw profile signals
    name = (
        ap.get("name")
        or " ".join(filter(None, [ap.get("first_name"), ap.get("last_name")]))
        or bd.get("name")
        or ""
    )
    company = (
        (ap.get("organization") or {}).get("name")
        or bd.get("current_company", {}).get("name") if isinstance(bd.get("current_company"), dict) else None
        or bd.get("current_company_name")
        or ""
    )
    title = ap.get("title") or bd.get("position") or bd.get("headline") or ""

    segment = guess_segment(title=title, company=company, headline=bd.get("headline", ""))

    # Stash extra signals in notes
    notes_parts = []
    if ap.get("email"):
        notes_parts.append(f"email={ap['email']}")
    phone = (ap.get("phone_numbers") or [{}])[0].get("sanitized_number") if ap.get("phone_numbers") else None
    if phone:
        notes_parts.append(f"phone={phone}")
    if segment:
        notes_parts.append(f"seg={segment}")
    if bd.get("country_code"):
        notes_parts.append(f"country={bd['country_code']}")
    if bd.get("followers"):
        notes_parts.append(f"li_followers={bd['followers']}")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return {
        "name":          name,
        "linkedin_url":  linkedin_url,
        "company":       company,
        "title_guess":   title,
        "intent":        "",          # set later by outreach.py qualify step
        "post_topic":    "",
        "comment_text":  "",
        "reply_status":  "pending",
        "dm_status":     "pending",
        "first_seen":    now,
        "last_touchpoint": "",
        "demo_requested": "",
        "demo_date":     "",
        "demo_outcome":  "",
        "deal_value":    "",
        "notes":         " | ".join(notes_parts),
    }


def append_to_leads_csv(row: dict) -> None:
    """Append a row, ensuring header is present. Skips duplicates by linkedin_url."""
    existing_urls = set()
    if LEADS_CSV.exists() and LEADS_CSV.stat().st_size > 0:
        with LEADS_CSV.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_urls = {r["linkedin_url"] for r in reader if r.get("linkedin_url")}

    if row["linkedin_url"] in existing_urls:
        print(f"  Skipping duplicate: {row['linkedin_url']}", file=sys.stderr)
        return

    write_header = not LEADS_CSV.exists() or LEADS_CSV.stat().st_size == 0
    with LEADS_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LEADS_CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def enrich_one(linkedin_url: str, dry_run: bool = False) -> dict:
    print(f"[1/3] Bright Data scrape: {linkedin_url}", file=sys.stderr)
    bd_profile = None
    try:
        snap_id = bd_trigger_li_profile(linkedin_url)
        results = bd_poll_snapshot(snap_id)
        bd_profile = results[0] if results else None
    except Exception as exc:
        print(f"  Bright Data failed: {exc}", file=sys.stderr)

    print(f"[2/3] Apollo people/match", file=sys.stderr)
    apollo_person = None
    try:
        apollo_person = apollo_people_match(linkedin_url=linkedin_url)
    except Exception as exc:
        print(f"  Apollo failed: {exc}", file=sys.stderr)

    row = merge_record(linkedin_url, bd_profile, apollo_person)

    # Persist raw API responses for debugging
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = ENRICH_LOG_DIR / f"{ts}_{linkedin_url.rstrip('/').rsplit('/', 1)[-1]}.json"
    log_path.write_text(json.dumps({
        "linkedin_url": linkedin_url,
        "brightdata": bd_profile,
        "apollo": apollo_person,
        "merged_row": row,
    }, indent=2, default=str), encoding="utf-8")
    print(f"  Raw response logged: {log_path.relative_to(ROOT)}", file=sys.stderr)

    print(f"[3/3] {'DRY RUN — would write' if dry_run else 'Writing'} to leads.csv", file=sys.stderr)
    if not dry_run:
        append_to_leads_csv(row)
    return row


def enrich_batch(path: Path, dry_run: bool = False) -> list[dict]:
    urls = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    pause = float(os.environ.get("ENRICH_RATE_LIMIT_SECS", "1.5"))
    rows = []
    for i, url in enumerate(urls, 1):
        print(f"\n── {i}/{len(urls)} ──", file=sys.stderr)
        rows.append(enrich_one(url, dry_run=dry_run))
        if i < len(urls):
            time.sleep(pause)
    return rows


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    one = sub.add_parser("one", help="Enrich a single LinkedIn URL")
    one.add_argument("url")
    one.add_argument("--dry-run", action="store_true")

    batch = sub.add_parser("batch", help="Enrich a file of LinkedIn URLs (one per line)")
    batch.add_argument("file", type=Path)
    batch.add_argument("--dry-run", action="store_true")

    args = p.parse_args()

    if args.cmd == "one":
        row = enrich_one(args.url, dry_run=args.dry_run)
        print(json.dumps(row, indent=2, default=str))
    else:
        rows = enrich_batch(args.file, dry_run=args.dry_run)
        print(json.dumps(rows, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
