"""Tests for the queue-hygiene guards (14-day auto-expire + no empty approvals)."""
import json
from datetime import datetime, timedelta, timezone

import pytest

import queue_hygiene as qh

NOW = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)


def _write(path, **fields):
    path.write_text(json.dumps(fields), encoding="utf-8")
    return path


# ── empty-body approval guard ───────────────────────────────────────────────

def test_is_empty_body():
    assert qh.is_empty_body({"post": ""})
    assert qh.is_empty_body({"post": "   \n  "})
    assert qh.is_empty_body({})
    assert not qh.is_empty_body({"post": "real content"})


def test_can_approve_rejects_empty_body():
    ok, why = qh.can_approve({"post": "", "status": "draft"})
    assert ok is False
    assert "empty" in why.lower()


def test_can_approve_rejects_published():
    ok, why = qh.can_approve({"post": "hi", "published": True})
    assert ok is False
    assert "published" in why.lower()


def test_can_approve_allows_normal_draft():
    ok, why = qh.can_approve({"post": "a real body", "status": "draft"})
    assert ok is True
    assert why == ""


@pytest.mark.parametrize("post", [
    {"post": "stale body", "status": "deleted", "rejected": True},   # purged draft
    {"post": "stale body", "status": "deleted"},                      # deleted, no flag
    {"post": "stale body", "status": "superseded"},                  # superseded variant
    {"post": "stale body", "rejected": True},                        # rejected flag only
])
def test_can_approve_refuses_rejected_or_removed(post):
    """A stale notification email's Approve button must not resurrect a dead draft."""
    ok, why = qh.can_approve(post)
    assert ok is False
    assert "reject" in why.lower() or "dead" in why.lower()


# ── age detection ───────────────────────────────────────────────────────────

def test_draft_datetime_prefers_generated_at():
    dt = qh.draft_datetime({"generated_at": "2026-07-01T09:00:00+00:00"}, "x.json")
    assert dt == datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)


def test_draft_datetime_falls_back_to_filename():
    dt = qh.draft_datetime({}, "20260601_083000_pain.json")
    assert dt == datetime(2026, 6, 1, 8, 30, tzinfo=timezone.utc)


def test_draft_datetime_handles_naive_generated_at():
    dt = qh.draft_datetime({"generated_at": "2026-07-10T00:00:00"}, "")
    assert dt.tzinfo is not None


def test_draft_age_days():
    post = {"generated_at": "2026-07-01T12:00:00+00:00"}
    assert qh.draft_age_days(post, NOW) == pytest.approx(14.0, abs=0.01)


# ── expire_stale ────────────────────────────────────────────────────────────

def test_expire_stale_rejects_old_and_keeps_fresh(tmp_path):
    d = tmp_path / "posts_history"
    d.mkdir()
    old = _write(d / "20260601_090000_pain.json",
                 post="old body", status="draft",
                 generated_at="2026-06-01T09:00:00+00:00")
    old_approved = _write(d / "20260610_090000_proof.json",
                          post="stale approved", status="approved", approved=True,
                          generated_at="2026-06-10T09:00:00+00:00")
    fresh = _write(d / "20260714_090000_vision.json",
                   post="fresh body", status="draft",
                   generated_at="2026-07-14T09:00:00+00:00")

    expired = qh.expire_stale([d], days=14, now=NOW)

    assert str(old) in expired and str(old_approved) in expired
    assert str(fresh) not in expired
    # Old drafts flipped to the canonical reject shape...
    o = json.loads(old.read_text(encoding="utf-8"))
    assert o["status"] == "deleted" and o["rejected"] is True and o["approved"] is False
    # ...including the stale APPROVED one (the leak this guard closes).
    oa = json.loads(old_approved.read_text(encoding="utf-8"))
    assert oa["rejected"] is True and oa["approved"] is False
    # Fresh draft untouched.
    fr = json.loads(fresh.read_text(encoding="utf-8"))
    assert fr["status"] == "draft" and "rejected" not in fr


def test_expire_stale_skips_terminal_and_published(tmp_path):
    d = tmp_path / "posts_history"
    d.mkdir()
    published = _write(d / "20260101_090000_pain.json",
                       post="x", published=True, status="published",
                       generated_at="2026-01-01T09:00:00+00:00")
    already = _write(d / "20260102_090000_proof.json",
                     post="x", status="deleted", rejected=True,
                     generated_at="2026-01-02T09:00:00+00:00")

    expired = qh.expire_stale([d], days=14, now=NOW)

    assert str(published) not in expired
    assert str(already) not in expired
    # Published record is not rewritten.
    p = json.loads(published.read_text(encoding="utf-8"))
    assert p["published"] is True and p["status"] == "published"


def test_expire_stale_dry_run_does_not_write(tmp_path):
    d = tmp_path / "posts_history"
    d.mkdir()
    old = _write(d / "20260601_090000_pain.json", post="old",
                 generated_at="2026-06-01T09:00:00+00:00")
    expired = qh.expire_stale([d], days=14, now=NOW, write=False)
    assert str(old) in expired
    # File unchanged in dry-run.
    assert json.loads(old.read_text(encoding="utf-8")) == {
        "post": "old", "generated_at": "2026-06-01T09:00:00+00:00"
    }


def test_expire_stale_idempotent(tmp_path):
    d = tmp_path / "posts_history"
    d.mkdir()
    _write(d / "20260601_090000_pain.json", post="old",
           generated_at="2026-06-01T09:00:00+00:00")
    first = qh.expire_stale([d], days=14, now=NOW)
    second = qh.expire_stale([d], days=14, now=NOW)
    assert len(first) == 1 and second == []
