"""Three-sequence outreach tracker for SmartPro Hub lead nurturing.

Segments:
  A — HR managers & business owners  (pain / proof / sanad pillars)
  B — Investors & government          (vision pillar)
  C — Tech founders & SaaS builders   (tech pillar)

Each prospect moves through a timed sequence of touch-points.  State is
persisted in outreach_tracker.json (or the path set by TRACKER_FILE env var).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Segment(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class Status(str, Enum):
    PENDING   = "pending"
    ACTIVE    = "active"
    REPLIED   = "replied"
    CONVERTED = "converted"
    OPTED_OUT = "opted_out"


# ---------------------------------------------------------------------------
# Sequence definitions — must match the LinkedIn playbook exactly (FIX A)
# ---------------------------------------------------------------------------

SEQUENCE_DAYS: dict[Segment, list[int]] = {
    Segment.A: [1, 4, 7, 9, 14],   # 5 touches over 14 days
    Segment.B: [1, 5, 8],           # 3 touches over 8 days
    Segment.C: [1, 3, 5],           # 3 touches over 5 days
}

SEQUENCE_ACTIONS: dict[Segment, list[str]] = {
    Segment.A: [
        "Like + genuine comment on their latest post (never 'great post')",
        "Share their post with a value-adding note — tag them",
        "Send connection request — no note needed",
        "Send first DM — value offer, no pitch (use Arabic template for Seg A)",
        "Follow-up — offer free 15-min SmartPRO Hub demo tailored to their sector",
    ],
    Segment.B: [
        "Comment on a Vision 2040 / digital Oman post they engaged with — be substantive",
        "Send connection request with note: 'Building Oman's first multi-tenant HR compliance platform — would value connecting'",
        "Send DM — attach 1-page PDF overview (not a pitch deck)",
    ],
    Segment.C: [
        "Comment on a #BuildInPublic or tech architecture post — reference a specific technical detail",
        "Send connection request — no note, let the comment do the work",
        "Send DM — peer conversation, no pitch (use English template for Seg C)",
    ],
}

# Fail loudly at import if the two dicts fall out of sync
for _seg in Segment:
    assert len(SEQUENCE_DAYS[_seg]) == len(SEQUENCE_ACTIONS[_seg]), (
        f"SEQUENCE_DAYS and SEQUENCE_ACTIONS length mismatch for segment {_seg}"
    )


# ---------------------------------------------------------------------------
# Store path — respects TRACKER_FILE env var so tests can use a temp file
# ---------------------------------------------------------------------------

def _store_path() -> Path:
    return Path(
        os.environ.get("TRACKER_FILE",
                       str(Path(__file__).parent / "outreach_tracker.json"))
    )


# ---------------------------------------------------------------------------
# Prospect dataclass
# ---------------------------------------------------------------------------

@dataclass
class Prospect:
    id:           str
    name:         str
    company:      str
    segment:      Segment
    started_at:   str           # ISO date, e.g. "2026-05-18"
    status:       str = Status.ACTIVE
    current_step: int = 0       # 0-based index into SEQUENCE_DAYS/ACTIONS
    notes:        str = ""
    tags:         list[str] = field(default_factory=list)
    converted_at: str = ""

    # ── Plain methods (not @property — avoids asdict/API inconsistency) ──

    def next_action_date(self) -> str | None:
        steps = SEQUENCE_DAYS.get(self.segment, [])
        if self.current_step >= len(steps):
            return None
        offset = steps[self.current_step]
        return (date.fromisoformat(self.started_at) + timedelta(days=offset)).isoformat()

    def next_action(self) -> str | None:
        actions = SEQUENCE_ACTIONS.get(self.segment, [])
        if self.current_step >= len(actions):
            return None
        return actions[self.current_step]

    def advance(self) -> bool:
        """Increment current_step. Returns True if still active, False if sequence finished."""
        self.current_step += 1
        if self.current_step >= len(SEQUENCE_DAYS.get(self.segment, [])):
            self.status = Status.REPLIED
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Ensure enum fields serialize as plain strings across all Python versions
        d["segment"] = d["segment"].value if isinstance(d["segment"], Enum) else d["segment"]
        d["status"]  = d["status"].value  if isinstance(d["status"],  Enum) else d["status"]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Prospect":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in d.items() if k in known}
        seg = filtered.get("segment", "A")
        filtered["segment"] = Segment(str(seg).upper()) if not isinstance(seg, Segment) else seg
        return cls(**filtered)


# ---------------------------------------------------------------------------
# Persistence — public names for external callers (FIX B)
# ---------------------------------------------------------------------------

def load_tracker() -> list[Prospect]:
    """Load all prospects from disk. Raises FileNotFoundError if store absent."""
    store = _store_path()
    if not store.exists():
        raise FileNotFoundError(f"Tracker file not found: {store}")
    raw: list[dict] = json.loads(store.read_text(encoding="utf-8"))
    return [Prospect.from_dict(r) for r in raw]


def save_tracker(prospects: list[Prospect]) -> None:
    _store_path().write_text(
        json.dumps([p.to_dict() for p in prospects], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_prospect(
    name: str,
    company: str,
    segment: Segment | str,
    prospect_id: str,
    started_at: str | None = None,
    notes: str = "",
    tags: list[str] | None = None,
) -> Prospect:
    """Enrol a new prospect; returns existing record silently if already enrolled."""
    try:
        prospects = load_tracker()
    except FileNotFoundError:
        prospects = []

    existing = next((p for p in prospects if p.id == prospect_id), None)
    if existing is not None:
        return existing

    if not isinstance(segment, Segment):
        segment = Segment(str(segment).upper())

    p = Prospect(
        id=prospect_id,
        name=name,
        company=company,
        segment=segment,
        started_at=started_at or date.today().isoformat(),
        notes=notes,
        tags=tags or [],
    )
    prospects.append(p)
    save_tracker(prospects)
    return p


def advance_prospect(prospect_id: str) -> dict:
    """Advance a prospect to their next sequence step.

    Saves to disk.  Returns the updated next-action dict, or a completion
    dict if the sequence is finished.
    """
    prospects = load_tracker()
    target = next((p for p in prospects if p.id == prospect_id), None)
    if target is None:
        raise ValueError(f"No prospect found with id '{prospect_id}'")

    still_active = target.advance()
    save_tracker(prospects)

    if not still_active:
        return {
            "status":       "sequence_complete",
            "prospect":     target.name,
            "final_status": target.status,
        }
    return {
        "status":           "advanced",
        "prospect":         target.name,
        "next_action_date": target.next_action_date(),
        "next_action":      target.next_action(),
        "step":             target.current_step + 1,
        "total_steps":      len(SEQUENCE_DAYS[target.segment]),
    }


def get_todays_actions(today: date | None = None) -> list[dict[str, Any]]:
    """Return all prospects whose next action is due today or overdue."""
    today = today or date.today()
    try:
        prospects = load_tracker()
    except FileNotFoundError:
        return []

    due: list[dict[str, Any]] = []
    for p in prospects:
        if p.status not in (Status.ACTIVE, Status.PENDING):
            continue
        nad = p.next_action_date()
        na  = p.next_action()
        if nad is None or na is None:
            continue
        action_date = date.fromisoformat(nad)
        if action_date <= today:
            due.append({
                "id":           p.id,
                "name":         p.name,
                "company":      p.company,
                "segment":      p.segment.value if isinstance(p.segment, Segment) else p.segment,
                "action":       na,
                "due_date":     nad,
                "overdue_days": (today - action_date).days,
                "current_step": p.current_step,
            })

    due.sort(key=lambda x: (-x["overdue_days"], x["segment"]))
    return due


def mark_converted(prospect_id: str) -> bool:
    try:
        prospects = load_tracker()
    except FileNotFoundError:
        return False
    for p in prospects:
        if p.id == prospect_id:
            p.status = Status.CONVERTED
            p.converted_at = datetime.now(timezone.utc).isoformat()
            save_tracker(prospects)
            return True
    return False


def mark_opted_out(prospect_id: str) -> bool:
    try:
        prospects = load_tracker()
    except FileNotFoundError:
        return False
    for p in prospects:
        if p.id == prospect_id:
            p.status = Status.OPTED_OUT
            save_tracker(prospects)
            return True
    return False


# ---------------------------------------------------------------------------
# KPI summary — consumed by dashboard.py
# ---------------------------------------------------------------------------

def kpi_summary() -> dict[str, Any]:
    """Return outreach KPIs.

    Raises FileNotFoundError if the tracker file has not been created yet
    (no prospects enrolled).  The dashboard catches this and shows a placeholder.
    """
    prospects = load_tracker()   # propagates FileNotFoundError intentionally
    total     = len(prospects)
    by_seg: dict[str, int] = {"A": 0, "B": 0, "C": 0}
    converted = opted_out = replied = active = 0

    for p in prospects:
        seg_key = p.segment.value if isinstance(p.segment, Segment) else str(p.segment)
        by_seg[seg_key] = by_seg.get(seg_key, 0) + 1
        if p.status == Status.CONVERTED:
            converted += 1
        elif p.status == Status.OPTED_OUT:
            opted_out += 1
        elif p.status == Status.REPLIED:
            replied += 1
        else:
            active += 1

    due_today = len(get_todays_actions())
    conv_rate = round(converted / total * 100, 1) if total else 0.0

    return {
        "total":           total,
        "active":          active,
        "converted":       converted,
        "opted_out":       opted_out,
        "replied":         replied,
        "by_segment":      by_seg,
        "conversion_rate": conv_rate,
        "due_today":       due_today,
    }
