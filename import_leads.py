#!/usr/bin/env python3
"""
import_leads.py — Add real LinkedIn profiles to outreach_tracker.json

Usage
-----
1. Create leads_input.txt with one lead per line in this format:
       URL | Name | Title | Company | Location
   Example:
       https://www.linkedin.com/in/ahmed-al-balushi-123/ | Ahmed Al-Balushi | HR Manager | Gulf Star LLC | Muscat

2. Run:
       python import_leads.py
   (reads leads_input.txt by default)

   Or pipe directly:
       python import_leads.py --file my_leads.txt

   Or pass raw text as argument (one line per lead, semicolon-separated):
       python import_leads.py --inline "URL1|Name1|Title1|Company1|City1;URL2|..."

Output
------
- Appends new entries to outreach_tracker.json (preserves existing mock data)
- Appends new rows to leads.csv
- Prints a summary table
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

TRACKER_FILE = Path(__file__).parent / "outreach_tracker.json"
LEADS_CSV    = Path(__file__).parent / "leads.csv"
INPUT_FILE   = Path(__file__).parent / "leads_input.txt"

TODAY = date.today().isoformat()

# ── Segment classification ─────────────────────────────────────────────────
_SEG_A_TITLE = re.compile(
    r"\b(hr|human resources|sanad|pro\b|payroll|labour|labor|wps|"
    r"manpower|recruitment|admin(?:istration)?|personnel|omanisation|"
    r"visa|permit|compliance officer)\b",
    re.I,
)
_SEG_A_COMPANY = re.compile(r"\b(sanad|pro services|hr solutions|manpower|staffing)\b", re.I)
_SEG_C_TITLE   = re.compile(r"\b(cto|chief technology|tech lead|engineer|developer|software|digital|it manager)\b", re.I)


def _segment(title: str, company: str) -> str:
    if _SEG_A_TITLE.search(title) or _SEG_A_COMPANY.search(company):
        return "A"
    if _SEG_C_TITLE.search(title):
        return "C"
    return "B"  # CEO / Owner / MD / Investor default


# ── Pain point by segment ──────────────────────────────────────────────────
_PAIN: dict[str, str] = {
    "A": "Manual WPS / permit tracking / MOL submissions across multiple clients",
    "B": "Month-end HR admin, payroll errors, multi-entity compliance overhead",
    "C": "GCC labour-law compliance at scale, multi-tenant HR edge cases",
}

# ── Language guess ─────────────────────────────────────────────────────────
_AR_SURNAME = re.compile(r"\b(al-|bin |bint |al |abu )", re.I)


def _lang(name: str) -> str:
    return "ar" if _AR_SURNAME.search(name) else "en"


# ── Tag builder ────────────────────────────────────────────────────────────
def _tags(title: str, company: str, location: str, segment: str) -> list[str]:
    tags: list[str] = []
    tl = title.lower()
    cl = company.lower()
    ll = location.lower()

    if "sanad" in tl or "sanad" in cl:
        tags.append("sanad")
    elif "pro" in tl or "pro" in cl:
        tags.append("pro-services")
    if "hr" in tl:
        tags.append("hr-manager" if "manager" in tl else "hr")
    if "ceo" in tl or "chief executive" in tl:
        tags.append("ceo")
    if "cto" in tl or "technology" in tl:
        tags.append("tech")
    if "founder" in tl:
        tags.append("founder")
    if "director" in tl or "md" == tl.strip() or "managing director" in tl:
        tags.append("director")
    if "muscat" in ll:
        tags.append("muscat")
    elif "sohar" in ll:
        tags.append("sohar")
    elif "nizwa" in ll:
        tags.append("nizwa")
    elif "dubai" in ll or "uae" in ll:
        tags.append("uae")
    if segment == "A":
        tags.append("priority-1")
    elif segment == "B":
        tags.append("priority-1" if "ceo" in tl or "owner" in tl or "founder" in tl else "priority-2")
    else:
        tags.append("priority-2")

    return tags or [segment.lower()]


# ── ID generation ──────────────────────────────────────────────────────────
def _next_ids(tracker: list[dict], count: int) -> list[str]:
    existing = [
        int(e["id"].split("-")[1]) for e in tracker if re.match(r"OA-\d+", e.get("id", ""))
    ]
    start = max(existing, default=0) + 1
    return [f"OA-{str(i).zfill(3)}" for i in range(start, start + count)]


# ── URL normaliser ─────────────────────────────────────────────────────────
def _normalise_url(raw: str) -> str:
    url = raw.strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url
    return url


# ── Parse input lines ──────────────────────────────────────────────────────
def parse_lines(lines: list[str]) -> list[dict]:
    leads = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            print(f"  SKIP (need at least URL|Name): {line[:60]}", file=sys.stderr)
            continue
        url      = _normalise_url(parts[0])
        name     = parts[1] if len(parts) > 1 else "Unknown"
        title    = parts[2] if len(parts) > 2 else "Unknown"
        company  = parts[3] if len(parts) > 3 else "Unknown"
        location = parts[4] if len(parts) > 4 else "Muscat"
        leads.append({"url": url, "name": name, "title": title, "company": company, "location": location})
    return leads


# ── Build tracker entry ────────────────────────────────────────────────────
def _build_entry(lead_id: str, lead: dict) -> dict:
    seg  = _segment(lead["title"], lead["company"])
    lang = _lang(lead["name"])
    pain = _PAIN[seg]
    return {
        "id":           lead_id,
        "name":         lead["name"],
        "company":      lead["company"],
        "linkedin_url": lead["url"],
        "segment":      seg,
        "started_at":   TODAY,
        "status":       "active",
        "current_step": 1,
        "notes":        (
            f"Title: {lead['title']} | Location: {lead['location']} | "
            f"Pain: {pain} | Lang: {lang}"
        ),
        "tags":         _tags(lead["title"], lead["company"], lead["location"], seg),
        "converted_at": "",
    }


# ── CSV row ────────────────────────────────────────────────────────────────
def _build_csv_row(lead: dict, entry: dict) -> dict:
    return {
        "name":            lead["name"],
        "linkedin_url":    lead["url"],
        "company":         lead["company"],
        "title_guess":     lead["title"],
        "intent":          "high",
        "post_topic":      "",
        "comment_text":    "",
        "reply_status":    "pending",
        "dm_status":       "step_1",
        "first_seen":      TODAY,
        "last_touchpoint": TODAY,
        "demo_requested":  "",
        "demo_date":       "",
        "demo_outcome":    "",
        "deal_value":      "",
        "notes":           f"Segment {entry['segment']} | {entry['notes']}",
    }


# ── Main ───────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Import LinkedIn leads into outreach_tracker.json")
    parser.add_argument("--file",   default=str(INPUT_FILE), help="Path to input file")
    parser.add_argument("--inline", default="",              help="Semicolon-separated lead strings")
    parser.add_argument("--dry-run", action="store_true",    help="Print what would be added, don't write")
    args = parser.parse_args()

    # Read input
    if args.inline:
        raw_lines = args.inline.split(";")
    else:
        src = Path(args.file)
        if not src.exists():
            print(f"Input file not found: {src}")
            print("Create leads_input.txt with lines like:")
            print("  https://www.linkedin.com/in/johndoe/ | John Doe | HR Manager | ACME LLC | Muscat")
            sys.exit(1)
        raw_lines = src.read_text(encoding="utf-8").splitlines()

    leads = parse_lines(raw_lines)
    if not leads:
        print("No valid leads found in input.")
        sys.exit(0)

    # Load tracker
    tracker: list[dict] = json.loads(TRACKER_FILE.read_text(encoding="utf-8")) if TRACKER_FILE.exists() else []

    # Check duplicates by URL
    existing_urls = {e.get("linkedin_url", "").rstrip("/") for e in tracker}
    new_leads = []
    for ld in leads:
        if ld["url"].rstrip("/") in existing_urls:
            print(f"  SKIP (already in tracker): {ld['url']}")
        else:
            new_leads.append(ld)

    if not new_leads:
        print("All provided URLs already exist in the tracker.")
        return

    # Assign IDs and build entries
    ids     = _next_ids(tracker, len(new_leads))
    entries = [_build_entry(ids[i], new_leads[i]) for i in range(len(new_leads))]

    # Print summary
    print(f"\n{'─'*70}")
    print(f"  Adding {len(entries)} lead(s) to tracker:")
    for e in entries:
        print(f"  {e['id']}  Seg {e['segment']}  {e['name']:<28}  {e['company']}")
    print(f"{'─'*70}\n")

    if args.dry_run:
        print("DRY RUN — nothing written.")
        return

    # Write tracker
    tracker.extend(entries)
    TRACKER_FILE.write_text(json.dumps(tracker, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ outreach_tracker.json updated ({len(tracker)} total entries)")

    # Write CSV
    csv_headers = [
        "name","linkedin_url","company","title_guess","intent","post_topic",
        "comment_text","reply_status","dm_status","first_seen","last_touchpoint",
        "demo_requested","demo_date","demo_outcome","deal_value","notes",
    ]
    existing_csv_names: set[str] = set()
    rows: list[dict] = []
    if LEADS_CSV.exists():
        with LEADS_CSV.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
                existing_csv_names.add(row.get("name", ""))

    for e, ld in zip(entries, new_leads):
        if e["name"] not in existing_csv_names:
            rows.append(_build_csv_row(ld, e))

    with LEADS_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(rows)
    print(f"✓ leads.csv updated ({len(rows)} total rows)")


if __name__ == "__main__":
    main()
