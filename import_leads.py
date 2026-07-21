#!/usr/bin/env python3
"""
import_leads.py — Import real LinkedIn leads into outreach_tracker.json + leads.csv

Usage:
    python import_leads.py                  # reads leads_input.txt
    python import_leads.py --dry-run        # preview without writing
    python import_leads.py --file my.txt    # use a different input file

Format of input file (one lead per line, skip # comments and blank lines):
    URL | Full Name | Job Title | Company Name | City
"""

import csv
import argparse
import sys
from datetime import date
from pathlib import Path

from atomic_io import load_json, write_json
from outreach_tracker import next_oa_id

BASE = Path(__file__).parent
TRACKER_FILE = BASE / "outreach_tracker.json"
LEADS_FILE   = BASE / "leads.csv"
DEFAULT_INPUT = BASE / "leads_input.txt"
TODAY = date.today().isoformat()

# ── Segment detection ─────────────────────────────────────────────────────────
SEG_B_KEYWORDS = ["investor", "investment", "fund", "venture", "capital", "vc", "angel"]
SEG_C_KEYWORDS = ["cto", "tech", "developer", "engineer", "saas", "digital", "software", "product manager"]
SEG_A_KEYWORDS = ["hr", "sanad", "pro ", "wps", "payroll", "admin", "operations", "cfo",
                  "managing director", "ceo", "owner", "founder", "director", "manager", "specialist"]

PAIN_MAP = {
    "sanad":             "Multi-client work permit tracking | Lang: ar",
    "pro":               "MOL submissions manual 15+ clients | Lang: ar",
    "hr manager":        "WPS payroll file 2+ days every month | Lang: en",
    "hr director":       "Omanisation ratios spreadsheet no real-time | Lang: en",
    "hr specialist":     "HR and PRO hats too much manual admin | Lang: en",
    "ceo":               "3+ hrs Monday HR admin | Lang: en",
    "cfo":               "Payroll errors employee disputes | Lang: en",
    "managing director": "HR PRO across multiple companies no unified view | Lang: en",
    "owner":             "Single HR person single point of failure | Lang: en",
    "founder":           "Client updates via WhatsApp clients feeling abandoned | Lang: en",
    "investor":          "Investor pitch Oman HR tech market Vision 2040 | Lang: en",
    "cto":               "Peer multi-tenant GCC compliance | Lang: en",
    "default":           "Manual HR/payroll admin taking too long | Lang: en",
}

TAG_MAP = {
    "sanad":    ["sanad", "muscat"],
    "pro":      ["pro-services", "muscat"],
    "hr":       ["hr-manager", "sme"],
    "ceo":      ["ceo", "sme"],
    "cfo":      ["cfo", "finance"],
    "investor": ["investor", "oman"],
    "cto":      ["tech-founder", "cto"],
    "founder":  ["founder", "startup"],
    "default":  ["oman", "sme"],
}


def detect_segment(title: str) -> str:
    t = title.lower()
    if any(k in t for k in SEG_B_KEYWORDS):
        return "B"
    if any(k in t for k in SEG_C_KEYWORDS):
        return "C"
    return "A"


def detect_pain(title: str) -> str:
    t = title.lower()
    for key, pain in PAIN_MAP.items():
        if key in t:
            return pain
    return PAIN_MAP["default"]


def detect_tags(title: str, city: str) -> list:
    t = title.lower()
    tags = []
    for key, tag_list in TAG_MAP.items():
        if key in t:
            tags = tag_list[:]
            break
    if not tags:
        tags = TAG_MAP["default"][:]
    city_l = city.lower()
    if city_l and city_l not in tags:
        tags.append(city_l)
    tags.append("priority-1")
    return tags


def parse_input_file(path: Path) -> list:
    leads = []
    errors = []
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 4:
                errors.append(f"  Line {lineno}: expected 4+ fields, got {len(parts)} → '{line}'")
                continue
            url, name, title, company = parts[0], parts[1], parts[2], parts[3]
            city = parts[4] if len(parts) > 4 else ""
            if not url.startswith("https://www.linkedin.com/in/"):
                errors.append(f"  Line {lineno}: URL doesn't look like a LinkedIn profile → '{url}'")
                continue
            leads.append({"url": url.rstrip("/"), "name": name, "title": title,
                          "company": company, "city": city})
    return leads, errors


def build_tracker_entry(lead: dict, new_id: str) -> dict:
    seg = detect_segment(lead["title"])
    pain = detect_pain(lead["title"])
    tags = detect_tags(lead["title"], lead["city"])
    location = lead["city"] if lead["city"] else "Oman"
    return {
        "id": new_id,
        "name": lead["name"],
        "linkedin_url": lead["url"],
        "company": lead["company"],
        "segment": seg,
        "started_at": TODAY,
        "status": "active",
        "current_step": 1,
        "notes": (f"{lead['company']} | Title: {lead['title']} | "
                  f"Location: {location} | Pain: {pain}"),
        "tags": tags,
        "converted_at": "",
    }


def build_csv_row(lead: dict, entry: dict) -> dict:
    return {
        "name": lead["name"],
        "linkedin_url": lead["url"],
        "company": lead["company"],
        "title_guess": lead["title"],
        "intent": "high" if entry["segment"] == "A" else "medium" if entry["segment"] == "B" else "low",
        "post_topic": "",
        "comment_text": "",
        "reply_status": "pending",
        "dm_status": "step_1",
        "first_seen": TODAY,
        "last_touchpoint": TODAY,
        "demo_requested": "",
        "demo_date": "",
        "demo_outcome": "",
        "deal_value": "",
        "notes": entry["notes"],
    }


def load_tracker() -> list:
    return load_json(TRACKER_FILE, default=[])


def save_tracker(tracker: list, dry_run: bool):
    if dry_run:
        return
    write_json(TRACKER_FILE, tracker)


def load_csv_urls() -> set:
    """Return set of existing linkedin_urls in leads.csv."""
    existing = set()
    if not LEADS_FILE.exists():
        return existing
    with open(LEADS_FILE, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("linkedin_url", "").strip().rstrip("/")
            if url:
                existing.add(url)
    return existing


def append_csv(rows: list, dry_run: bool):
    if dry_run or not rows:
        return
    fieldnames = ["name","linkedin_url","company","title_guess","intent","post_topic",
                  "comment_text","reply_status","dm_status","first_seen","last_touchpoint",
                  "demo_requested","demo_date","demo_outcome","deal_value","notes"]
    file_exists = LEADS_FILE.exists()
    with open(LEADS_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Import LinkedIn leads into tracker")
    parser.add_argument("--file", default=str(DEFAULT_INPUT), help="Input file path")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"❌  Input file not found: {input_path}")
        sys.exit(1)

    print(f"📂  Reading: {input_path}")
    leads, errors = parse_input_file(input_path)

    if errors:
        print("\n⚠️  Parse errors (these lines skipped):")
        for e in errors:
            print(e)

    if not leads:
        print("\n⚠️  No valid leads found. Check format: URL | Name | Title | Company | City")
        sys.exit(0)

    print(f"\n✅  Parsed {len(leads)} lead(s)")

    tracker = load_tracker()
    existing_tracker_urls = {p.get("linkedin_url", "").rstrip("/") for p in tracker}
    existing_csv_urls = load_csv_urls()

    added = []
    skipped = []

    for lead in leads:
        url = lead["url"].rstrip("/")
        if url in existing_tracker_urls or url in existing_csv_urls:
            skipped.append(lead["name"])
            continue
        new_id = next_oa_id(tracker)
        entry = build_tracker_entry(lead, new_id)
        csv_row = build_csv_row(lead, entry)
        tracker.append(entry)
        existing_tracker_urls.add(url)
        added.append((entry, csv_row))

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Results:")
    print(f"  ➕  Adding  : {len(added)}")
    print(f"  ⏭️  Skipped : {len(skipped)} (duplicates)")
    if skipped:
        print(f"     → {', '.join(skipped)}")

    print()
    for entry, _ in added:
        seg_label = {"A": "🟢 Buyer", "B": "🟡 Investor", "C": "🔵 Tech Peer"}[entry["segment"]]
        print(f"  {entry['id']}  {entry['name']} | {entry['company']} | Seg {seg_label}")
        print(f"       {entry['linkedin_url']}")

    if not added:
        print("Nothing new to add.")
        sys.exit(0)

    save_tracker(tracker, args.dry_run)
    append_csv([row for _, row in added], args.dry_run)

    if not args.dry_run:
        print(f"\n✅  Saved {len(added)} lead(s) to outreach_tracker.json + leads.csv")
        print(f"   Next cron run will start Segment sequences for these {len(added)} prospect(s).")
    else:
        print("\n[DRY RUN] Nothing written. Remove --dry-run to commit changes.")


if __name__ == "__main__":
    main()
