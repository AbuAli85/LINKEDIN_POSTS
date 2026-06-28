"""Single source of truth for SmartPRO promo URLs + UTM tracking.

Every outbound link in generated posts and first comments should come from here
so the URLs can't drift across modules (previously the same paths were
re-typed in content_strategy.py, company_content_strategy.py, publisher.py and
generator.py). Override the base host via the SMARTPRO_BASE_URL env var (e.g. for
a staging domain) without touching code.

Helpers:
  url(key)              -> "https://www.thesmartpro.io/demo"            (canonical, no tracking)
  display(key)          -> "www.thesmartpro.io/demo"                    (scheme-less, for in-prose mentions)
  tracked(key, camp)    -> ".../demo?utm_source=linkedin&...&utm_campaign=pain"   (campaign known now)
  tracked_template(key) -> ".../demo?...&utm_campaign={campaign}"        (literal {campaign} for str.format)
"""
from __future__ import annotations

import os
from urllib.parse import quote

BASE = os.environ.get("SMARTPRO_BASE_URL", "https://www.thesmartpro.io").rstrip("/")
BRAND_HOST = BASE.split("://", 1)[-1]                       # e.g. "www.thesmartpro.io"
WHATSAPP = os.environ.get("SMARTPRO_WHATSAPP", "+96879665522")

UTM_SOURCE = "linkedin"
UTM_MEDIUM = "social"

# Canonical paths, keyed by short name. "home" is the bare host.
PATHS = {
    "home": "",
    "demo": "/demo",
    "sanad": "/sanad/assistant",
    "feasibility": "/feasibility-studio",
    "investors": "/investors",
    "partners": "/partners",
    "careers": "/careers",
}


def url(key: str) -> str:
    """Fully-qualified canonical URL (with scheme), no tracking params."""
    return BASE + PATHS[key]


def display(key: str) -> str:
    """Human-readable URL without the scheme (for in-prose brand mentions)."""
    return BRAND_HOST + PATHS[key]


def tracked(key: str, campaign: str, *, source: str = UTM_SOURCE, medium: str = UTM_MEDIUM) -> str:
    """Canonical URL with UTM params filled in (campaign already known)."""
    return f"{url(key)}?utm_source={source}&utm_medium={medium}&utm_campaign={campaign}"


def tracked_template(key: str, *, source: str = UTM_SOURCE, medium: str = UTM_MEDIUM) -> str:
    """Like tracked() but leaves a literal {campaign} placeholder for str.format()."""
    return f"{url(key)}?utm_source={source}&utm_medium={medium}&utm_campaign={{campaign}}"


def whatsapp(prefill: str | None = None) -> str:
    """Return a wa.me link for WHATSAPP number (clickable, RTL-safe).

    With prefill, appends ?text=... so the lead's first message is pre-written
    and you know the chat came from LinkedIn.
    """
    num = WHATSAPP.lstrip("+").replace(" ", "")
    base = f"https://wa.me/{num}"
    return f"{base}?text={quote(prefill)}" if prefill else base
