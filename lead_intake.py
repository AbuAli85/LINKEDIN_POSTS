#!/usr/bin/env python3
"""lead_intake.py — turn demo bookings into ready-to-send, attributed follow-ups.

A demo booking is your hottest signal: a real person, with contact details, who
came from a specific post. This connector reads `bookings.json`, and for every
booking that carries contact info it drafts a personalized first follow-up
(email + LinkedIn DM + WhatsApp message), tags it with the post that drove it,
and saves it under `lead_followups/`. It is idempotent — each booking is drafted
once (flagged `followup_drafted`).

    python lead_intake.py            # draft follow-ups for new contactable bookings
    python lead_intake.py list       # show every booking + contact + status
    python lead_intake.py show 1     # print a drafted follow-up in full

Honest scope: this acts on people who *converted* (booked) — not on anonymous
link clicks, which carry no identity. See README / CAL_WEBHOOK_SETUP.md.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import links
from atomic_io import load_json, write_json
from outreach_tracker import next_oa_id

ROOT = Path(__file__).resolve().parent
BOOKINGS = ROOT / "bookings.json"
FOLLOWUPS_DIR = ROOT / "lead_followups"
LEADS_CSV = ROOT / "leads.csv"
TRACKER_FILE = ROOT / "outreach_tracker.json"

# leads.csv columns (must match import_leads.py / outreach.py exactly)
CSV_FIELDS = [
    "name", "linkedin_url", "company", "title_guess", "intent", "post_topic",
    "comment_text", "reply_status", "dm_status", "first_seen", "last_touchpoint",
    "demo_requested", "demo_date", "demo_outcome", "deal_value", "notes",
]


# ---------------------------------------------------------------------------
# Booking helpers
# ---------------------------------------------------------------------------


def _load_bookings() -> list[dict]:
    try:
        return json.loads(BOOKINGS.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return []


def _save_bookings(bookings: list[dict]) -> None:
    write_json(BOOKINGS, bookings)


def _has_contact(b: dict) -> bool:
    return bool(b.get("email") or b.get("linkedin") or b.get("phone"))


def _is_arabic(b: dict) -> bool:
    camp = (b.get("utm_campaign") or "").lower()
    return camp.endswith("-ar") or camp.endswith("_ar") or "_ar" in camp


def _first_name(b: dict) -> str:
    name = (b.get("name") or "").strip()
    return name.split()[0] if name else ""


# campaign prefix -> (EN topic, AR topic) the booker cared about
_TOPIC = {
    "pain":        ("payroll and HR operations", "الرواتب وإدارة الموارد البشرية"),
    "sanad":       ("Sanad office workflows and case tracking", "سير عمل مكاتب سند وتتبع المعاملات"),
    "proof":       ("the results other Oman teams are seeing", "النتائج التي تحققها فرق عُمانية أخرى"),
    "vision":      ("where Oman operations are heading", "وجهة العمليات في عُمان"),
    "tech":        ("the platform and how it is built", "المنصة وكيفية بنائها"),
    "feasibility": ("your feasibility study", "دراسة الجدوى الخاصة بك"),
    "product":     ("how SmartPRO Hub fits your operation", "كيف تناسب SmartPRO Hub عملك"),
}


def _topic(b: dict) -> tuple[str, str]:
    camp = (b.get("utm_campaign") or "").lower()
    for key, pair in _TOPIC.items():
        if camp.startswith(key):
            return pair
    return ("how SmartPRO Hub fits your operation", "كيف تناسب SmartPRO Hub عملك")


# ---------------------------------------------------------------------------
# Follow-up drafting (template-based, bilingual, formal Arabic)
# ---------------------------------------------------------------------------


def _draft(b: dict) -> dict:
    ar = _is_arabic(b)
    fn = _first_name(b)
    topic_en, topic_ar = _topic(b)
    company = (b.get("company") or "").strip()

    if ar:
        hi = f"مرحباً {fn}،" if fn else "مرحباً،"
        co = f" في {company}" if company else ""
        email_subject = "بخصوص عرض SmartPRO Hub التجريبي"
        email_body = (
            f"{hi}\n\n"
            f"شكراً لحجزك عرض SmartPRO Hub التجريبي. سعدنا باهتمامك بعد متابعتك منشورنا على LinkedIn.\n\n"
            f"خلال اللقاء سنستعرض {topic_ar}، وكيف يمكن لـ SmartPRO Hub أن يخدم فريقك{co} بشكل عملي.\n\n"
            f"حتى نُحضّر اللقاء بما يناسبك: ما أكثر تحدٍّ تشغيلي يستهلك وقتكم هذا الشهر؟\n\n"
            f"إن رغبت في تجربة المنصة مباشرةً قبل اللقاء: {links.url('demo')}\n\n"
            f"مع التحية،\nفريق SmartPRO Hub"
        )
        linkedin_dm = (
            f"{hi} شكراً لحجزك عرض SmartPRO Hub التجريبي. سنستعرض {topic_ar}. "
            f"ما أكثر تحدٍّ تشغيلي يشغلكم حالياً حتى نُركّز عليه في اللقاء؟"
        )
        whatsapp = f"{hi} هذا فريق SmartPRO Hub — تأكيد لحجزك العرض التجريبي. نتطلع للقائك."
    else:
        hi = f"Hi {fn}," if fn else "Hi,"
        co = f" at {company}" if company else ""
        email_subject = "About your SmartPRO Hub demo"
        email_body = (
            f"{hi}\n\n"
            f"Thanks for booking a SmartPRO Hub demo — glad the LinkedIn post landed.\n\n"
            f"In the session we'll walk through {topic_en}, and how SmartPRO Hub would work for your team{co} in practice.\n\n"
            f"So I can tailor it: what's the one operational task eating the most time this month?\n\n"
            f"If you'd like to try the platform before we meet: {links.url('demo')}\n\n"
            f"Best,\nThe SmartPRO Hub team"
        )
        linkedin_dm = (
            f"{hi} thanks for booking the SmartPRO Hub demo. We'll cover {topic_en}. "
            f"What's the one operational task eating the most time right now, so I can focus the session on it?"
        )
        whatsapp = f"{hi} this is the SmartPRO Hub team — confirming your demo booking. Looking forward to it."

    channels = {}
    if b.get("email"):
        channels["email"] = {"to": b["email"], "subject": email_subject, "body": email_body}
    if b.get("linkedin"):
        channels["linkedin_dm"] = {"to": b["linkedin"], "message": linkedin_dm}
    if b.get("phone"):
        num = re.sub(r"[^\d]", "", b["phone"])
        channels["whatsapp"] = {"to": b["phone"], "link": links.whatsapp(whatsapp) if num else "", "message": whatsapp}
    return channels


def _slug(b: dict) -> str:
    base = (b.get("name") or b.get("email") or "lead").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "lead"


# ---------------------------------------------------------------------------
# Outreach integration — push booked leads into leads.csv + outreach_tracker.json
# so outreach.py send-sequences runs the full multi-touch sequence.
# ---------------------------------------------------------------------------

import csv  # noqa: E402


def _segment(b: dict) -> str:
    camp = (b.get("utm_campaign") or "").lower()
    if camp.startswith(("vision", "investor")):
        return "B"
    if camp.startswith("tech"):
        return "C"
    return "A"  # buyers (HR managers / owners) — the demo-booker default


def _load_tracker() -> list[dict]:
    return load_json(TRACKER_FILE, default=[])


def _csv_keys() -> tuple[set[str], set[str]]:
    """Return (linkedin_urls, names) already present in leads.csv for dedup."""
    urls, names = set(), set()
    if LEADS_CSV.exists():
        with open(LEADS_CSV, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("linkedin_url"):
                    urls.add(row["linkedin_url"].rstrip("/"))
                if row.get("name"):
                    names.add(row["name"].strip().lower())
    return urls, names


def _push_to_outreach(b: dict) -> str:
    """Add a booked lead to leads.csv (+ tracker if LinkedIn-reachable).

    Returns a short status string for the run summary. Idempotent: dedup by
    linkedin_url (or name when no URL), and skips bookings already pushed.
    """
    url = (b.get("linkedin") or "").strip().rstrip("/")
    name = (b.get("name") or "").strip()
    today = (b.get("booked_at") or datetime.now(timezone.utc).isoformat())[:10]
    seg = _segment(b)
    contact_note = " | ".join(filter(None, [
        f"email: {b['email']}" if b.get("email") else "",
        f"phone: {b['phone']}" if b.get("phone") else "",
    ]))
    notes = (f"Demo booked via LinkedIn post '{b.get('utm_campaign') or '?'}' "
             f"on {today}. {contact_note}").strip()

    csv_urls, csv_names = _csv_keys()
    dup = (url and url in csv_urls) or (not url and name.lower() in csv_names)
    if not dup:
        with open(LEADS_CSV, "a", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writerow({
                "name": name or (b.get("email") or "Demo lead"),
                "linkedin_url": url, "company": b.get("company", ""),
                "title_guess": "", "intent": "high",
                "post_topic": b.get("utm_campaign", ""), "comment_text": "",
                "reply_status": "demo_booked", "dm_status": "step_1" if url else "no_linkedin",
                "first_seen": today, "last_touchpoint": today,
                "demo_requested": "yes", "demo_date": today, "demo_outcome": "",
                "deal_value": "", "notes": notes,
            })

    # Only LinkedIn-reachable leads can enter the (LinkedIn) send-sequences engine.
    if not url:
        return "leads.csv only (no LinkedIn URL — use the email/WhatsApp draft)"

    tracker = _load_tracker()
    if any((p.get("linkedin_url", "").rstrip("/") == url) for p in tracker):
        return "already in sequence"
    tracker.append({
        "id": next_oa_id(tracker),
        "name": name or "Demo lead",
        "linkedin_url": url,
        "company": b.get("company", ""),
        "segment": seg,
        "started_at": today,
        "status": "active",
        "current_step": 1,
        "notes": notes,
        "tags": ["demo-booked", f"seg-{seg.lower()}", "priority-1"],
        "converted_at": "",
    })
    write_json(TRACKER_FILE, tracker)
    return f"queued in sequence (Seg {seg})"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_intake() -> int:
    bookings = _load_bookings()
    FOLLOWUPS_DIR.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)
    drafted = 0
    skipped_no_contact = 0

    for b in bookings:
        if b.get("followup_drafted"):
            continue
        if not _has_contact(b):
            skipped_no_contact += 1
            continue
        channels = _draft(b)
        ts = (b.get("booked_at") or now.isoformat()).replace(":", "").replace("-", "")[:15]
        fname = f"{ts}_{_slug(b)}.json"
        record = {
            "drafted_at": now.isoformat(),
            "lead": {k: b.get(k, "") for k in
                     ("name", "email", "phone", "linkedin", "company", "message")},
            "source": {
                "channel": "demo_booking",
                "event_type": b.get("event_type", ""),
                "booked_at": b.get("booked_at", ""),
                "post_campaign": b.get("utm_campaign", ""),
            },
            "language": "ar" if _is_arabic(b) else "en",
            "followups": channels,
            "status": "draft",
        }
        write_json(FOLLOWUPS_DIR / fname, record)
        outreach_status = _push_to_outreach(b)
        b["followup_drafted"] = True
        b["followup_file"] = f"lead_followups/{fname}"
        b["outreach_status"] = outreach_status
        drafted += 1
        who = b.get("name") or b.get("email") or b.get("phone")
        print(f"  + {who}  (from {b.get('utm_campaign') or 'unknown post'})")
        print(f"      follow-up drafted -> {b['followup_file']}")
        print(f"      outreach          -> {outreach_status}")

    _save_bookings(bookings)
    print(f"\n{drafted} new lead(s) processed.")
    if drafted:
        print("LinkedIn-reachable leads are queued in outreach_tracker.json — run the")
        print("sequence with:  python outreach.py send-sequences   (LINKEDIN_DRY_RUN=true to preview)")
    if skipped_no_contact:
        print(f"{skipped_no_contact} booking(s) had no contact details — relay isn't "
              f"forwarding attendee fields yet (see CAL_WEBHOOK_SETUP.md).")
    if drafted:
        print("Review and send:  python lead_intake.py show 1")
    return 0


def _contactable(bookings: list[dict]) -> list[dict]:
    return [b for b in bookings if _has_contact(b)]


def cmd_list() -> int:
    bookings = _load_bookings()
    if not bookings:
        print("\nNo bookings recorded yet.\n")
        return 0
    print(f"\n{len(bookings)} booking(s) — {len(_contactable(bookings))} with contact details:\n")
    for i, b in enumerate(bookings, 1):
        who = b.get("name") or "(no name)"
        contact = b.get("email") or b.get("phone") or b.get("linkedin") or "— no contact —"
        status = "drafted" if b.get("followup_drafted") else ("ready" if _has_contact(b) else "anon")
        print(f"  [{i:>2}] {who:<24} {contact:<28} <- {b.get('utm_campaign') or '?':<14} [{status}]")
    print("\n  Draft follow-ups:  python lead_intake.py")
    return 0


def cmd_show(selector: str) -> int:
    drafts = sorted(FOLLOWUPS_DIR.glob("*.json")) if FOLLOWUPS_DIR.exists() else []
    if not drafts:
        print("\nNo follow-ups drafted yet. Run `python lead_intake.py` first.\n")
        return 1
    if selector.isdigit() and 1 <= int(selector) <= len(drafts):
        path = drafts[int(selector) - 1]
    else:
        match = [d for d in drafts if selector.lower() in d.name.lower()]
        if not match:
            print(f"\nNo follow-up matches '{selector}'.\n")
            return 1
        path = match[0]
    r = json.loads(path.read_text(encoding="utf-8-sig"))
    lead = r["lead"]
    print(f"\n=== Follow-up for {lead.get('name') or lead.get('email')} "
          f"({r['language']}) — from post '{r['source'].get('post_campaign')}' ===")
    print(f"file: {path.name}")
    for ch, data in r["followups"].items():
        print(f"\n--- {ch.upper()} -> {data.get('to','')}")
        if data.get("subject"):
            print(f"Subject: {data['subject']}")
        if data.get("link"):
            print(f"Link: {data['link']}")
        print(data.get("body") or data.get("message") or "")
    print()
    return 0


def main(argv: list[str]) -> int:
    cmd = (argv[1] if len(argv) > 1 else "intake").lower()
    if cmd in ("intake", "run", ""):
        return cmd_intake()
    if cmd in ("list", "ls"):
        return cmd_list()
    if cmd in ("show", "read"):
        if len(argv) < 3:
            print("Usage: python lead_intake.py show <number>")
            return 1
        return cmd_show(argv[2])
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
