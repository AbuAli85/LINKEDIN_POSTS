"""Regression tests for the Link & Pricing fix sprint.

Covers:
  Fix 1 — stale public pricing (no "OMR 25"/"OMR 60" in strategy/prompt modules;
          PRICING is the single source of truth).
  Fix 2 — links.py: apex BASE, /book helper + type validation, careers removed,
          https-only CTAs, no bare www.thesmartpro.io token.
  Fix 3 — one primary CTA per post (<= 2 https:// links in a body).
"""
from pathlib import Path

import pytest

import links
import smartpro_data
import content_strategy as cs
import company_content_strategy as ccs
import generator

ROOT = Path(__file__).parent

# Modules whose string output ends up inside a published post or its prompt.
STRATEGY_MODULES = [
    "content_strategy.py",
    "company_content_strategy.py",
    "generator.py",
    "newsletter.py",
]


# ── Fix 1: pricing ──────────────────────────────────────────────────────────

def test_pricing_constant_matches_platform():
    assert smartpro_data.PRICING == {"starter": 12, "business": 49, "enterprise": 149}


@pytest.mark.parametrize("fname", STRATEGY_MODULES)
def test_no_stale_prices_in_strategy_modules(fname):
    """No stale OMR 25 / OMR 60 (Business/Enterprise) anywhere in a prompt module."""
    src = (ROOT / fname).read_text(encoding="utf-8")
    assert "OMR 25" not in src, f"{fname} still advertises stale Business price OMR 25"
    assert "OMR 60" not in src, f"{fname} still advertises stale Enterprise price OMR 60"
    # Arabic stale forms too.
    assert "٢٥ ريال" not in src, f"{fname} still advertises stale Arabic OMR 25"
    assert "٦٠ ريال" not in src, f"{fname} still advertises stale Arabic OMR 60"


def test_current_prices_only_via_constant():
    """The correct numbers must not be hardcoded as 'OMR NN' literals in prompt modules —
    they should only ever appear via smartpro_data.PRICING-derived sentences."""
    for fname in STRATEGY_MODULES:
        src = (ROOT / fname).read_text(encoding="utf-8")
        for literal in ("OMR 12", "OMR 49", "OMR 149"):
            assert literal not in src, (
                f"{fname} hardcodes {literal!r} — build the sentence from "
                "smartpro_data.PRICING instead."
            )


def test_pricing_sentence_uses_correct_numbers():
    s = smartpro_data.PRICING_SENTENCE_EN
    assert "OMR 12/month" in s and "OMR 49/month" in s and "OMR 149/month" in s
    # "from" phrasing is always the starter price.
    assert smartpro_data.PRICING_FROM_EN == "from OMR 12/month"


# ── Fix 2: links ────────────────────────────────────────────────────────────

def test_base_is_apex_no_www():
    assert links.BASE == "https://thesmartpro.io"
    assert "www." not in links.BASE
    assert "www." not in links.BRAND_HOST


def test_book_path_present_careers_removed():
    assert links.PATHS["book"] == "/book"
    assert "careers" not in links.PATHS
    # Deleting the key must break any caller that still references it.
    with pytest.raises(KeyError):
        links.url("careers")


def test_book_helper_builds_tracked_url():
    u = links.book("demo", "pain")
    assert u.startswith("https://thesmartpro.io/book?type=demo")
    assert "utm_source=linkedin" in u
    assert "utm_medium=social" in u
    assert "utm_campaign=pain" in u


def test_book_template_leaves_campaign_placeholder():
    t = links.book_template("partner")
    assert "utm_campaign={campaign}" in t
    assert t.format(campaign="q3").endswith("utm_campaign=q3")


@pytest.mark.parametrize("bad", ["", "webinar", "call", "Demo", "meeting"])
def test_book_rejects_invalid_type(bad):
    with pytest.raises(ValueError):
        links.book(bad, "x")
    with pytest.raises(ValueError):
        links.book_template(bad)


@pytest.mark.parametrize("good", ["demo", "consultation", "partner"])
def test_book_accepts_valid_types(good):
    assert links.book(good, "x").startswith("https://")


@pytest.mark.parametrize("fname", STRATEGY_MODULES + ["links.py", "smartpro_data.py"])
def test_no_bare_www_token(fname):
    src = (ROOT / fname).read_text(encoding="utf-8")
    assert "www.thesmartpro.io" not in src, f"{fname} contains a bare www.thesmartpro.io token"


def _all_cta_blocks():
    """Every _cta_block output across personal + company pillars, both languages."""
    out = []
    for strat in (cs, ccs):
        for name, cfg in strat.PILLARS.items():
            # generator._cta_block reads the ACTIVE strategy via load_strategy();
            # default is personal. Exercise personal pillars directly, and company
            # pillars are exercised in the dedicated company test below.
            if strat is cs:
                out.append(generator._cta_block({**cfg, "name": name}))
    return [c for c in out if c]


def test_every_personal_cta_uses_https():
    """No scheme-less clickable link — every CTA carries a full https:// URL and
    no bare scheme-less thesmartpro.io token."""
    import re
    for cta in _all_cta_blocks():
        assert "https://" in cta, f"CTA has no https link: {cta!r}"
        # A scheme-less domain would be preceded by a non-'/' char (or start).
        assert not re.search(r"(?:^|[^/])www\.thesmartpro\.io", cta), cta
        assert not re.search(r"(?:^|[^/:])thesmartpro\.io", cta), (
            f"CTA contains a scheme-less thesmartpro.io token: {cta!r}"
        )


def test_company_partner_cta_uses_book_partner():
    """The company partnership pillar's CTA is book?type=partner (not investors)."""
    import os
    # _cta_block reads the active strategy via LINKEDIN_AUDIENCE (not cached).
    os.environ["LINKEDIN_AUDIENCE"] = "company"
    try:
        cfg = {**ccs.PILLARS["partnership"], "name": "partnership"}
        block = generator._cta_block(cfg)
        assert "https://thesmartpro.io/book?type=partner" in block
    finally:
        os.environ.pop("LINKEDIN_AUDIENCE", None)


# ── Fix 3: one primary CTA per post ─────────────────────────────────────────

def _body(extra_links: int) -> str:
    """An 800+ char body carrying `extra_links` https:// URLs."""
    filler = "SmartPRO Hub keeps Oman payroll and compliance in one place. " * 20
    links_block = "\n".join(f"https://thesmartpro.io/x{i}" for i in range(extra_links))
    return filler + "\n" + links_block + "\n#SmartPROHub"


def test_count_links():
    assert generator.count_links(_body(0)) == 0
    assert generator.count_links(_body(2)) == 2
    assert generator.count_links(_body(3)) == 3


def test_validate_rejects_more_than_two_links():
    assert generator._validate(_body(3)) is not None
    err = generator._validate(_body(3))
    assert "too many links" in err


def test_validate_allows_up_to_two_links():
    # Two links (primary CTA + WhatsApp) is the allowed maximum.
    assert generator._validate(_body(2)) is None
    assert generator._validate(_body(1)) is None
