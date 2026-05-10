"""Check whether tomorrow's scheduled publish slot has an approved draft.

Run by .github/workflows/empty-slot-reminder.yml on Sun/Tue/Thu at 5pm UTC
(9pm Muscat) — 12 hours before each Mon/Wed/Fri publish window.

Exits 0 in all cases (failures should never break CI); sends an alert via
notifier.send_empty_slot_alert() when no approved draft is found.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _is_approved_for(path: Path, pillar: str) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return (
            data.get("pillar") == pillar
            and (data.get("approved") or data.get("status") == "approved")
            and not data.get("published")
        )
    except Exception:
        return False


def main() -> int:
    try:
        from content_strategy import PILLARS
    except ImportError as exc:
        print(f"ERROR: could not import content_strategy: {exc}")
        return 0

    tomorrow    = datetime.now(timezone.utc) + timedelta(days=1)
    weekday     = tomorrow.weekday()  # 0=Mon … 6=Sun
    publish_date = tomorrow.strftime("%Y-%m-%d")

    # Find which scheduled pillar publishes tomorrow (conversion is manual-only)
    todays_pillar = next(
        (name for name, cfg in PILLARS.items()
         if cfg.get("weekday") == weekday and cfg.get("generate_weekday", -1) >= 0),
        None,
    )

    if todays_pillar is None:
        print(f"No pillar scheduled for tomorrow (weekday={weekday}). Nothing to do.")
        return 0

    print(f"Tomorrow is {publish_date} (weekday={weekday}), scheduled pillar: {todays_pillar}")

    history  = Path(__file__).parent / "posts_history"
    approved = any(
        _is_approved_for(f, todays_pillar)
        for f in sorted(history.glob("*.json"), reverse=True)
    )

    if approved:
        print(f"Approved {todays_pillar!r} draft found. Slot is filled — no alert needed.")
        return 0

    print(f"No approved {todays_pillar!r} draft for {publish_date}. Sending alert...")
    try:
        from notifier import send_empty_slot_alert
        send_empty_slot_alert(pillar=todays_pillar, publish_date=publish_date)
        print("Alert sent.")
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: alert failed: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
