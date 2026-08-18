"""The publish sweep's date matching, and that the whole campaign fires in order.

publish_day is a recurring weekday name. A campaign post meant for the second
Friday would fire on the first one — seven days early and out of sequence —
so publish_date pins a post to one calendar day and wins over publish_day.
"""
import json
from datetime import date, timedelta

import pytest

import main


def _draft(tmp_path, name, **fields):
    post = {"post": "body", "approved": True, "status": "approved",
            "published": False, "pillar": "proof"}
    post.update(fields)
    p = tmp_path / name
    p.write_text(json.dumps(post), encoding="utf-8")
    return p


@pytest.fixture
def swept(tmp_path, monkeypatch):
    """Run publish_approved in DRY_RUN against a scratch history dir."""
    monkeypatch.setattr(main, "_history_dir", lambda: tmp_path)
    monkeypatch.setattr(main, "_expire_stale_drafts", lambda: None)
    monkeypatch.setenv("DRY_RUN", "true")
    return tmp_path


def _candidate(capsys):
    """The file the sweep chose this run, or None."""
    for line in capsys.readouterr().out.splitlines():
        if line.startswith("[publish_approved] Candidate:"):
            return line.split("Candidate:")[1].split()[0]
    return None


def _freeze(monkeypatch, when):
    class _DT(main.datetime):
        @classmethod
        def now(cls, tz=None):
            return when
    monkeypatch.setattr(main, "datetime", _DT)


from datetime import datetime, timezone

WED_19 = datetime(2026, 8, 19, 5, 15, tzinfo=timezone.utc)
FRI_21 = datetime(2026, 8, 21, 5, 15, tzinfo=timezone.utc)
FRI_28 = datetime(2026, 8, 28, 5, 15, tzinfo=timezone.utc)


def test_pinned_post_does_not_fire_on_the_earlier_matching_weekday(swept, monkeypatch, capsys):
    """The regression this field exists for."""
    _draft(swept, "day10.json", publish_day="Friday", publish_date="2026-08-28")
    _freeze(monkeypatch, FRI_21)
    main.publish_approved_for_today()
    assert _candidate(capsys) is None


def test_pinned_post_fires_on_its_own_date(swept, monkeypatch, capsys):
    _draft(swept, "day10.json", publish_day="Friday", publish_date="2026-08-28")
    _freeze(monkeypatch, FRI_28)
    main.publish_approved_for_today()
    assert _candidate(capsys) == "day10.json"


def test_unpinned_post_still_matches_on_weekday(swept, monkeypatch, capsys):
    _draft(swept, "legacy.json", publish_day="Friday")
    _freeze(monkeypatch, FRI_21)
    main.publish_approved_for_today()
    assert _candidate(capsys) == "legacy.json"


def test_post_with_no_schedule_at_all_is_never_stuck(swept, monkeypatch, capsys):
    _draft(swept, "nolegacy.json")
    _freeze(monkeypatch, FRI_21)
    main.publish_approved_for_today()
    assert _candidate(capsys) == "nolegacy.json"


def test_pinned_beats_a_contradicting_weekday(swept, monkeypatch, capsys):
    """publish_date is authoritative even when publish_day disagrees."""
    _draft(swept, "odd.json", publish_day="Monday", publish_date="2026-08-19")
    _freeze(monkeypatch, WED_19)
    main.publish_approved_for_today()
    assert _candidate(capsys) == "odd.json"


def test_rejected_pinned_post_is_skipped(swept, monkeypatch, capsys):
    _draft(swept, "dead.json", publish_day="Friday", publish_date="2026-08-28",
           rejected=True, status="deleted")
    _freeze(monkeypatch, FRI_28)
    main.publish_approved_for_today()
    assert _candidate(capsys) is None


def test_the_whole_campaign_fires_in_campaign_order(swept, monkeypatch, capsys):
    """Six posts, one sweep per day, must come out 1, 2, 4, 6, 8, 10."""
    plan = [(1, "2026-08-19"), (2, "2026-08-20"), (4, "2026-08-22"),
            (6, "2026-08-24"), (8, "2026-08-26"), (10, "2026-08-28")]
    for i, (day, iso) in enumerate(plan):
        _draft(swept, f"{i:02d}_day{day}.json",
               publish_day=date.fromisoformat(iso).strftime("%A"),
               publish_date=iso, campaign_day=day)

    fired = []
    cur = date(2026, 8, 19)
    for _ in range(14):
        _freeze(monkeypatch, datetime(cur.year, cur.month, cur.day, 5, 15, tzinfo=timezone.utc))
        main.publish_approved_for_today()
        if chosen := _candidate(capsys):
            fired.append((cur.isoformat(), int(chosen.split("day")[1].split(".")[0])))
        cur += timedelta(days=1)

    assert [d for _, d in fired] == [1, 2, 4, 6, 8, 10]
    assert [iso for iso, _ in fired] == [iso for _, iso in plan]
