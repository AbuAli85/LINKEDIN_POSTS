"""Tests for the approval and published notifications, and the schedule they quote.

The notifier is deliberately best-effort — it must never raise into the
generate, approve, or publish path. These tests pin that contract along with
the payload each event carries.
"""
import os
from datetime import datetime, timezone

import pytest

import notifier

# 2026-08-18 is a Tuesday.
TUESDAY_NOON = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
TUESDAY_EARLY = datetime(2026, 8, 18, 4, 0, 0, tzinfo=timezone.utc)

DRAFT = {
    "pillar": "proof",
    "topic": "Document expiry alerts ship bilingual",
    "post": "An expiry alert that names the wrong document is worse than no alert.",
    "char_count": 68,
    "publish_day": "Wednesday",
    "approved_at": "2026-08-18T12:33:59+00:00",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """No notifier config leaks in from the developer's shell or CI."""
    for var in (
        "RESEND_API_KEY", "NOTIFY_EMAIL", "NOTIFY_FROM", "NOTIFY_WEBHOOK_URL",
        "NOTIFY_ON_DRAFT", "DASHBOARD_URL", "APPROVED_VIA",
        "GITHUB_ACTIONS", "GITHUB_ACTOR", "GITHUB_REPOSITORY",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def captured(monkeypatch):
    """Intercept _dispatch so tests assert payloads without sending anything."""
    calls = []
    monkeypatch.setattr(
        notifier,
        "_dispatch",
        lambda context, subject, html_body, text_body, label: calls.append(
            {"context": context, "subject": subject,
             "html": html_body, "text": text_body, "label": label}
        ),
    )
    return calls


# ── publish schedule ────────────────────────────────────────────────────────

def test_next_slot_is_the_sweep_cron_not_the_backup():
    """05:15 UTC is the sweep; 06:00 is only the backup pass."""
    slot = notifier.next_publish_slot("Wednesday", TUESDAY_NOON)
    assert (slot.hour, slot.minute) == (notifier.SWEEP_HOUR_UTC, notifier.SWEEP_MINUTE_UTC)
    assert (slot.hour, slot.minute) == (5, 15)
    assert slot.date() == datetime(2026, 8, 19).date()


def test_same_day_before_the_slot_publishes_today():
    slot = notifier.next_publish_slot("Tuesday", TUESDAY_EARLY)
    assert slot.date() == datetime(2026, 8, 18).date()


def test_same_day_after_the_slot_waits_a_full_week():
    """A Tuesday draft approved after 05:15 must not claim today's sweep."""
    slot = notifier.next_publish_slot("Tuesday", TUESDAY_NOON)
    assert slot.date() == datetime(2026, 8, 25).date()


@pytest.mark.parametrize("day", ["", None, "someday", "Wed"])
def test_unknown_publish_day_returns_none(day):
    assert notifier.next_publish_slot(day, TUESDAY_NOON) is None


def test_format_publish_slot_carries_utc_and_muscat():
    text = notifier.format_publish_slot("Wednesday", TUESDAY_NOON)
    assert "05:15 UTC" in text
    assert "09:15 Muscat" in text


def test_format_publish_slot_says_so_when_unscheduled():
    assert "no publish_day" in notifier.format_publish_slot("", TUESDAY_NOON)


# ── permalink ───────────────────────────────────────────────────────────────

def test_permalink_matches_the_dashboard_form():
    urn = "urn:li:share:7490650036813438976"
    assert notifier.linkedin_permalink(urn) == (
        f"https://www.linkedin.com/feed/update/{urn}/"
    )


@pytest.mark.parametrize("post_id", ["", "   ", None])
def test_permalink_empty_when_no_share_id(post_id):
    assert notifier.linkedin_permalink(post_id) == ""


# ── who approved ────────────────────────────────────────────────────────────

def test_approval_source_prefers_explicit_surface(monkeypatch):
    monkeypatch.setenv("APPROVED_VIA", "panel.py approve — fahad@muscat")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert notifier.approval_source() == "panel.py approve — fahad@muscat"


def test_approval_source_names_the_actions_actor(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_ACTOR", "AbuAli85")
    source = notifier.approval_source()
    assert "AbuAli85" in source
    assert "approve_draft" in source


def test_approval_source_falls_back_to_local_shell():
    assert "local CLI" in notifier.approval_source()


# ── approval notification ───────────────────────────────────────────────────

def test_approved_notice_carries_title_schedule_and_approver(captured, monkeypatch):
    monkeypatch.setenv("APPROVED_VIA", "panel.py approve — fahad@muscat")
    notifier.send_draft_approved("posts_history/20260818_122149_proof.json", DRAFT)

    assert len(captured) == 1
    ctx = captured[0]["context"]
    assert ctx["event"] == "draft_approved"
    assert ctx["title"] == "Document expiry alerts ship bilingual"
    assert ctx["approved_by"] == "panel.py approve — fahad@muscat"
    assert "05:15 UTC" in ctx["scheduled_for"]
    assert ctx["draft_path"] == "posts_history/20260818_122149_proof.json"
    assert "Document expiry alerts" in captured[0]["subject"]
    # The scheduled time must survive into both rendered bodies, not just the JSON.
    assert "05:15 UTC" in captured[0]["text"]
    assert "05:15 UTC" in captured[0]["html"]


def test_approved_notice_uses_the_recorded_approver_over_the_environment(captured, monkeypatch):
    """A draft approved elsewhere keeps its own approved_by."""
    monkeypatch.setenv("APPROVED_VIA", "some other shell")
    notifier.send_draft_approved(
        "posts_history/x_proof.json", {**DRAFT, "approved_by": "GitHub Actions — AbuAli85"}
    )
    assert captured[0]["context"]["approved_by"] == "GitHub Actions — AbuAli85"


def test_approved_notice_says_nothing_is_posted_yet(captured):
    notifier.send_draft_approved("posts_history/x_proof.json", DRAFT)
    assert "Nothing has been posted yet" in captured[0]["text"]


# ── published notification ──────────────────────────────────────────────────

def test_published_notice_carries_the_live_url(captured):
    published = {
        **DRAFT,
        "post_id": "urn:li:share:7490650036813438976",
        "published_at": "2026-08-19T05:15:12+00:00",
        "cta_comment_posted": True,
    }
    notifier.send_post_published("posts_history/20260818_122149_proof.json", published)

    ctx = captured[0]["context"]
    assert ctx["event"] == "post_published"
    assert ctx["linkedin_url"] == (
        "https://www.linkedin.com/feed/update/urn:li:share:7490650036813438976/"
    )
    assert ctx["cta_comment_posted"] is True
    assert ctx["linkedin_url"] in captured[0]["text"]
    assert ctx["linkedin_url"] in captured[0]["html"]
    assert captured[0]["subject"].startswith("Published — ")


def test_published_notice_is_honest_when_linkedin_returned_no_id(captured):
    notifier.send_post_published("posts_history/x_proof.json", {**DRAFT, "post_id": ""})
    assert captured[0]["context"]["linkedin_url"] == ""
    assert "no share id" in captured[0]["text"]


# ── muting and failure containment ──────────────────────────────────────────

@pytest.mark.parametrize("value", ["false", "0", "no", "off", "FALSE"])
def test_notify_on_draft_mutes_both_new_events(captured, monkeypatch, value):
    monkeypatch.setenv("NOTIFY_ON_DRAFT", value)
    notifier.send_draft_approved("posts_history/x_proof.json", DRAFT)
    notifier.send_post_published("posts_history/x_proof.json", DRAFT)
    assert captured == []


def test_dispatch_without_config_skips_quietly(capsys):
    notifier._dispatch({"event": "test"}, "subject", "<p>html</p>", "text", "Test")
    out = capsys.readouterr().out
    assert "email skipped" in out
    assert "webhook skipped" in out


def test_dispatch_survives_a_broken_webhook(monkeypatch, capsys):
    """A dead webhook must not raise into the caller that just published a post."""
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "https://example.invalid/hook")

    def _boom(*args, **kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(notifier.requests, "post", _boom)
    notifier._dispatch({"event": "test"}, "subject", "<p>html</p>", "text", "Test")
    assert "webhook failed" in capsys.readouterr().out


# ── titles ──────────────────────────────────────────────────────────────────

def test_title_falls_back_to_the_opening_line_without_a_topic():
    title = notifier._post_title({"post": "First line here.\nSecond line.", "pillar": "proof"})
    assert title == "First line here."


def test_title_falls_back_to_the_pillar_for_an_empty_post():
    assert notifier._post_title({"post": "", "pillar": "proof"}) == "proof"


def test_long_titles_are_truncated():
    title = notifier._post_title({"topic": "x" * 200})
    assert len(title) == 90
    assert title.endswith("...")
