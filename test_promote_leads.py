"""Tests for auto-promotion of high-intent commenters into the outreach tracker.

The promotion step is the bridge that did not exist: cmd_qualify scored a
commenter "high" and nothing entered outreach_tracker.json, which is the file
send-sequences reads. These tests pin the promotion rule, the dedupe key, and
the boundary with export (which owns leads.csv).
"""
import json

import pytest

import outreach


def _comment_file(tmp_path, name, url, intent, title="HR Manager", company="Acme LLC", score=9):
    payload = {
        "post_topic": "Document expiry alerts",
        "comments": [{
            "commenter_name": name,
            "commenter_linkedin_url": url,
            "comment_text": "How does this handle multi-branch licences?",
            "qualification": {
                "intent": intent, "score": score,
                "title_guess": title, "company_guess": company,
            },
        }],
    }
    p = tmp_path / f"{name.lower().replace(' ', '_')}_comments.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


@pytest.fixture
def wired(tmp_path, monkeypatch):
    """Point the module's tracker + comment dir at a scratch directory."""
    tracker = tmp_path / "outreach_tracker.json"
    tracker.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(outreach, "TRACKER_FILE", tracker)
    monkeypatch.setattr(outreach, "_all_comment_files", lambda: sorted(tmp_path.glob("*_comments.json")))
    return tmp_path, tracker


def _tracker(path):
    return json.loads(path.read_text(encoding="utf-8"))


# ── the promotion rule ──────────────────────────────────────────────────────

def test_high_intent_lead_is_promoted(wired):
    tmp, tracker = wired
    _comment_file(tmp, "Aisha Said", "https://www.linkedin.com/in/aisha-said", "high")
    outreach.cmd_promote_leads()

    leads = _tracker(tracker)
    assert len(leads) == 1
    assert leads[0]["name"] == "Aisha Said"
    assert leads[0]["company"] == "Acme LLC"
    assert leads[0]["status"] == "active"
    assert leads[0]["current_step"] == 1          # enters the DM sequence at step 1
    assert "auto-promoted" in leads[0]["tags"]
    assert "high-intent" in leads[0]["tags"]


@pytest.mark.parametrize("intent", ["medium", "low", "", None])
def test_only_high_intent_is_promoted(wired, intent):
    """Export covers high+medium; promotion is high only, per the decision."""
    tmp, tracker = wired
    _comment_file(tmp, "Sami Nasser", "https://www.linkedin.com/in/sami-nasser", intent)
    outreach.cmd_promote_leads()
    assert _tracker(tracker) == []


def test_real_qualification_data_is_kept_not_slug_guessed(wired):
    """The manual-capture path guesses from the URL slug; promotion must not."""
    tmp, tracker = wired
    _comment_file(tmp, "Layla Al Balushi", "https://www.linkedin.com/in/layla-b",
                  "high", title="CFO", company="Gulf Freight LLC")
    outreach.cmd_promote_leads()

    lead = _tracker(tracker)[0]
    assert lead["company"] == "Gulf Freight LLC"   # not "Unknown Company"
    assert "CFO" in lead["notes"]
    assert "Payroll errors" in lead["notes"]       # pain mapped from the real title


def test_segment_comes_from_the_title(wired):
    tmp, tracker = wired
    _comment_file(tmp, "Omar Vc", "https://www.linkedin.com/in/omar-vc", "high", title="Angel investor")
    _comment_file(tmp, "Noor Cto", "https://www.linkedin.com/in/noor-cto", "high", title="CTO")
    _comment_file(tmp, "Hind Hr", "https://www.linkedin.com/in/hind-hr", "high", title="HR Manager")
    outreach.cmd_promote_leads()

    by_name = {l["name"]: l["segment"] for l in _tracker(tracker)}
    assert by_name == {"Omar Vc": "B", "Noor Cto": "C", "Hind Hr": "A"}


# ── dedupe on profile URL ───────────────────────────────────────────────────

def test_rerunning_the_scan_does_not_double_add(wired):
    tmp, tracker = wired
    _comment_file(tmp, "Aisha Said", "https://www.linkedin.com/in/aisha-said", "high")
    outreach.cmd_promote_leads()
    outreach.cmd_promote_leads()
    outreach.cmd_promote_leads()
    assert len(_tracker(tracker)) == 1


@pytest.mark.parametrize("variant", [
    "https://www.linkedin.com/in/aisha-said/",
    "https://linkedin.com/in/aisha-said",
    "https://www.linkedin.com/in/aisha-said?utm_source=li",
    "HTTPS://WWW.LINKEDIN.COM/in/aisha-said",
    "linkedin.com/in/aisha-said",
])
def test_url_variants_are_the_same_lead(wired, variant):
    """A manually captured lead must block the promoted duplicate and vice versa."""
    tmp, tracker = wired
    tracker.write_text(json.dumps([{
        "id": "OA-021", "name": "Aisha Said",
        "linkedin_url": "https://www.linkedin.com/in/aisha-said",
        "status": "active", "current_step": 2,
    }]), encoding="utf-8")
    _comment_file(tmp, "Aisha Said", variant, "high")
    outreach.cmd_promote_leads()

    leads = _tracker(tracker)
    assert len(leads) == 1
    assert leads[0]["current_step"] == 2    # existing sequence progress untouched


def test_lead_without_a_profile_url_is_skipped(wired):
    """No URL means no dedupe key and nothing to DM."""
    tmp, tracker = wired
    _comment_file(tmp, "Anon", "", "high")
    outreach.cmd_promote_leads()
    assert _tracker(tracker) == []


def test_ids_do_not_collide_with_existing_tracker_entries(wired):
    tmp, tracker = wired
    tracker.write_text(json.dumps([
        {"id": "OA-021", "linkedin_url": "https://www.linkedin.com/in/someone-else"},
        {"id": "OA-042", "linkedin_url": "https://www.linkedin.com/in/another-one"},
    ]), encoding="utf-8")
    _comment_file(tmp, "New Lead", "https://www.linkedin.com/in/new-lead", "high")
    outreach.cmd_promote_leads()

    ids = [l["id"] for l in _tracker(tracker)]
    assert ids == ["OA-021", "OA-042", "OA-043"]
    assert len(set(ids)) == len(ids)


# ── boundaries ──────────────────────────────────────────────────────────────

def test_dry_run_writes_nothing(wired):
    tmp, tracker = wired
    _comment_file(tmp, "Aisha Said", "https://www.linkedin.com/in/aisha-said", "high")
    outreach.cmd_promote_leads(dry_run=True)
    assert _tracker(tracker) == []


def test_promotion_does_not_touch_leads_csv(wired, monkeypatch, tmp_path):
    """export owns leads.csv; appending here would duplicate every row."""
    csv_path = tmp_path / "leads.csv"
    csv_path.write_text("name,linkedin_url\n", encoding="utf-8")
    monkeypatch.setattr(outreach, "LEADS_CSV", csv_path)
    before = csv_path.read_text(encoding="utf-8")

    tmp, _ = wired
    _comment_file(tmp, "Aisha Said", "https://www.linkedin.com/in/aisha-said", "high")
    outreach.cmd_promote_leads()
    assert csv_path.read_text(encoding="utf-8") == before


def test_a_corrupt_comment_file_does_not_stop_the_others(wired):
    tmp, tracker = wired
    (tmp / "broken_comments.json").write_text("{not json", encoding="utf-8")
    _comment_file(tmp, "Aisha Said", "https://www.linkedin.com/in/aisha-said", "high")
    outreach.cmd_promote_leads()
    assert len(_tracker(tracker)) == 1


# ── the shared URL normaliser ───────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("https://www.linkedin.com/in/x/", "https://www.linkedin.com/in/x"),
    ("https://linkedin.com/in/x", "https://www.linkedin.com/in/x"),
    ("https://www.linkedin.com/in/x?trk=abc", "https://www.linkedin.com/in/x"),
    ("  https://www.linkedin.com/in/X  ", "https://www.linkedin.com/in/x"),
    ("", ""),
    (None, ""),
])
def test_normalise_profile_url(raw, expected):
    assert outreach.normalise_profile_url(raw) == expected
