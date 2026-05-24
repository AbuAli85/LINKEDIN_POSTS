# migrate_outreach_tracker.py
# One-time migration: renames legacy field names in outreach_tracker.json
# Run once after deploying Fix C. Safe to run multiple times (idempotent).
# Usage: python migrate_outreach_tracker.py [--path path/to/outreach_tracker.json]

import json
import os
import shutil
import argparse
from datetime import datetime

FIELD_MAP = {
    "linkedin_id": "id",
    "sequence_idx": "current_step",
}

# Fields added in the new schema that legacy records lack.
# Values are sentinels — edit before running if you have real data.
FILL_DEFAULTS = {
    "company":    "",           # fill in manually after migration if known
    "started_at": "2026-01-01", # placeholder; set to actual enrol date
}

def migrate(path: str) -> None:
    if not os.path.exists(path):
        print(f"No file at '{path}' — nothing to migrate.")
        return

    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError(f"Expected a JSON array at root of '{path}', got {type(records)}")

    # Backup before touching anything
    backup_path = f"{path}.bak.{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}"
    shutil.copy2(path, backup_path)
    print(f"Backup written to: {backup_path}")

    changed = 0
    for i, record in enumerate(records):
        # Rename legacy keys
        for old_key, new_key in FIELD_MAP.items():
            if old_key in record:
                record[new_key] = record.pop(old_key)
                changed += 1
                print(f"  Record {i} ({record.get('name', '?')}): '{old_key}' -> '{new_key}'")
        # Backfill new required fields missing from legacy records
        for key, default in FILL_DEFAULTS.items():
            if key not in record:
                record[key] = default
                changed += 1
                print(f"  Record {i} ({record.get('name', '?')}): added '{key}' = {default!r}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    if changed == 0:
        print("No legacy fields found — file is already up to date.")
    else:
        print(f"Done. {changed} field(s) renamed across {len(records)} record(s).")
        print(f"Original backed up at: {backup_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate outreach_tracker.json field names.")
    parser.add_argument(
        "--path",
        default="outreach_tracker.json",
        help="Path to outreach_tracker.json (default: ./outreach_tracker.json)",
    )
    args = parser.parse_args()
    migrate(args.path)
