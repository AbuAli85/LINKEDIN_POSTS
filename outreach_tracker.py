"""Three-sequence outreach tracker for SmartPro Hub lead nurturing.

Segments:
  A — HR managers & business owners  (pain / proof / sanad pillars)
  B — Investors & government          (vision pillar)
  C — Tech founders & SaaS builders   (tech pillar)

Each prospect moves through a timed sequence of touch-points.  The tracker
persists state in outreach_tracker.json (git-committed alongside other data).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

_STORE = Path(__file__).parent / "outreach_tracker.json"

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
# Sequence definitions
# ---------------------------------------------------------------------------
# Each list entry: (day_offset, action_label)
# day_offset is relative to the prospect's enroll_date.

SEQUENCE_DAYS: dict[str, list[tuple[int, str]]] = {
    Segment.A: [
        (0,  "connect_request"),
        (3,  "welcome_dm"),
        (7,  "value_share"),       # share a pain-point post or case study
        (14, "soft_pitch"),        # SmartPro trial offer
        (21, "follow_up"),
        (30, "final_touch"),
    ],
    Segment.B: [
        (0,  "connect_request"),
        (5,  "welcome_dm"),
        (10, "insight_share"),     # Vision 2040 / compliance angle
        (18, "demo_invite"),
        (28, "follow_up"),
    ],
    Segment.C: [
        (0,  "connect_request"),
        (2,  "welcome_dm"),        # faster cadence for tech founders
        (6,  "build_in_public"),   # link to tech pillar post
        (12, "collab_offer"),      # co-build / API partner angle
        (20, "follow_up"),
    ],
}

SEQUENCE_ACTIONS: dict[str, dict[str, str]] = {
    Segment.A: {
        "connect_request": "Send LinkedIn connection request mentioning SmartPro Hub",
        "welcome_dm":       "Send welcome DM: introduce SmartPro, ask about current HR pain",
        "value_share":      "Share a relevant pain-point post or WPS compliance tip",
        "soft_pitch":       "Offer 14-day free trial: www.thesmartpro.io",
        "follow_up":        "Check in — any questions about the trial?",
        "final_touch":      "Final value nudge — share a customer proof story",
    },
    Segment.B: {
        "connect_request": "Send LinkedIn connection request (Vision 2040 / compliance angle)",
        "welcome_dm":       "Welcome DM: SmartPro supports Ministry of Labour compliance",
        "insight_share":    "Share Vision 2040 workforce insight or Omanization update",
        "demo_invite":      "Invite to live product demo (personalised calendar link)",
        "follow_up":        "Follow-up after demo — any questions or blockers?",
    },
    Segment.C: {
        "connect_request": "Send LinkedIn connection request (fellow builder angle)",
        "welcome_dm":       "Welcome DM: reference their stack / recent build-in-public post",
        "build_in_public":  "Share tech pillar post — tRPC/Drizzle architecture thread",
        "collab_offer":     "Propose API partnership or integration collaboration",
        "follow_up":        "Check in — interested in SmartPro early-adopter plan?",
    },
}


# ---------------------------------------------------------------------------
# Prospect dataclass
# ---------------------------------------------------------------------------

@dataclass
class Prospect:
    linkedin_id:  str
    name:         str
    segment:      str                       # "A" | "B" | "C"
    enroll_date:  str                       # ISO date string, e.g. "2026-05-18"
    status:       str  = Status.ACTIVE      # Status enum value
    sequence_idx: int  = 0                  # index into SEQUENCE_DAYS[segment]
    notes:        str  = ""
    tags:         list[str] = field(default_factory=list)
    last_action:  str  = ""
    last_action_date: str = ""
    converted_at: str  = ""

    # convenience ─────────────────────────────────────────────────────────
    @property
    def enroll(self) -> date:
        return date.fromisoformat(self.enroll_date)

    @property
    def next_action(self) -> tuple[str, date] | None:
        seq = SEQUENCE_DAYS.get(self.segment, [])
        if self.sequence_idx >= len(seq):
            return None
        day_offset, action = seq[self.sequence_idx]
        return action, self.enroll + timedelta(days=day_offset)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Prospect":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _load() -> list[Prospect]:
    if not _STORE.exists():
        return []
    try:
        raw: list[dict] = json.loads(_STORE.read_text(encoding="utf-8"))
        return [Prospect.from_dict(r) for r in raw]
    except Exception:
        return []


def _save(prospects: list[Prospect]) -> None:
    _STORE.write_text(
        json.dumps([p.to_dict() for p in prospects], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_prospect(
    linkedin_id: str,
    name: str,
    segment: str,
    enroll_date: str | None = None,
    notes: str = "",
    tags: list[str] | None = None,
) -> Prospect:
    """Enrol a new prospect; skip silently if already enrolled."""
    prospects = _load()
    if any(p.linkedin_id == linkedin_id for p in prospects):
        return next(p for p in prospects if p.linkedin_id == linkedin_id)

    seg = (segment or "A").strip().upper()
    if seg not in (s.value for s in Segment):
        seg = "A"

    p = Prospect(
        linkedin_id=linkedin_id,
        name=name,
        segment=seg,
        enroll_date=enroll_date or date.today().isoformat(),
        notes=notes,
        tags=tags or [],
    )
    prospects.append(p)
    _save(prospects)
    return p


def get_todays_actions(today: date | None = None) -> list[dict[str, Any]]:
    """Return all prospects whose next sequence action is due today or overdue."""
    today = today or date.today()
    due: list[dict[str, Any]] = []

    for p in _load():
        if p.status not in (Status.ACTIVE, Status.PENDING):
            continue
        na = p.next_action
        if na is None:
            continue
        action, action_date = na
        if action_date <= today:
            due.append({
                "linkedin_id":   p.linkedin_id,
                "name":          p.name,
                "segment":       p.segment,
                "action":        action,
                "action_label":  SEQUENCE_ACTIONS.get(p.segment, {}).get(action, action),
                "due_date":      action_date.isoformat(),
                "overdue_days":  (today - action_date).days,
                "sequence_idx":  p.sequence_idx,
            })

    due.sort(key=lambda x: (x["overdue_days"] * -1, x["segment"]))
    return due


def mark_action_done(linkedin_id: str, notes: str = "") -> bool:
    """Advance a prospect's sequence index after completing an action."""
    prospects = _load()
    for p in prospects:
        if p.linkedin_id != linkedin_id:
            continue
        seq = SEQUENCE_DAYS.get(p.segment, [])
        if p.sequence_idx < len(seq):
            _, action = seq[p.sequence_idx]
            p.last_action = action
            p.last_action_date = date.today().isoformat()
            if notes:
                p.notes = (p.notes + "\n" + notes).strip()
        p.sequence_idx += 1
        if p.sequence_idx >= len(seq):
            p.status = Status.REPLIED   # sequence exhausted; awaiting reply
        _save(prospects)
        return True
    return False


def mark_converted(linkedin_id: str) -> bool:
    prospects = _load()
    for p in prospects:
        if p.linkedin_id == linkedin_id:
            p.status = Status.CONVERTED
            p.converted_at = datetime.now(timezone.utc).isoformat()
            _save(prospects)
            return True
    return False


def mark_opted_out(linkedin_id: str) -> bool:
    prospects = _load()
    for p in prospects:
        if p.linkedin_id == linkedin_id:
            p.status = Status.OPTED_OUT
            _save(prospects)
            return True
    return False


# ---------------------------------------------------------------------------
# KPI summary (consumed by dashboard.py)
# ---------------------------------------------------------------------------

def kpi_summary() -> dict[str, Any]:
    """Return outreach KPIs for embedding in the dashboard KPI panel.

    Keys
    ----
    total           — total prospects enrolled
    active          — currently in-sequence
    converted       — marked converted
    opted_out       — opted out
    replied         — sequence exhausted, awaiting reply
    by_segment      — {"A": int, "B": int, "C": int}
    conversion_rate — converted / total (0–100 %)
    due_today       — number of actions due today or overdue
    """
    prospects = _load()
    total     = len(prospects)
    by_seg: dict[str, int] = {"A": 0, "B": 0, "C": 0}
    converted = 0
    opted_out = 0
    replied   = 0
    active    = 0

    for p in prospects:
        by_seg[p.segment] = by_seg.get(p.segment, 0) + 1
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
