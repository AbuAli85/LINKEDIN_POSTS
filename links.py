"""Single source of truth for SmartPRO promo URLs + UTM tracking.

Every outbound link in generated posts and first comments should come from here
so the URLs can't drift across modules (previously the same paths were
re-typed in content_strategy.py, company_content_strategy.py, publisher.py and
generator.py). Override the base host via the SMARTPRO_BASE_URL env var (e.g. for
a staging domain) without touching code.

Helpers:
  url(key)              -> "https://thesmartpro.io/demo"                (canonical, no tracking)
  display(key)          -> "thesmartpro.io/demo"                        (scheme-less, brand mentions only)
  tracked(key, camp)    -> ".../demo?utm_source=linkedin&...&utm_campaign=pain"   (campaign known now)
  tracked_template(key) -> ".../demo?...&utm_campaign={campaign}"        (literal {campaign} for str.format)
  book(type_, camp)     -> ".../book?type=demo&utm_...&utm_campaign=pain"          (booking CTA, clickable)
  book_template(type_)  -> ".../book?type=demo&utm_...&utm_campaign={campaign}"    (booking CTA template)

NOTE: BASE is the apex host (no www). The site 301s www -> apex, so linking the
apex directly skips a redirect hop. display() is for pure brand mentions only —
LinkedIn does not reliably linkify scheme-less URLs, so every clickable CTA must
use a full https:// URL from url()/tracked()/book().
"""
from __future__ import annotations

import os
from urllib.parse import quote

BASE = os.environ.get("SMARTPRO_BASE_URL", "https://thesmartpro.io").rstrip("/")
BRAND_HOST = BASE.split("://", 1)[-1]                       # e.g. "thesmartpro.io"
WHATSAPP = os.environ.get("SMARTPRO_WHATSAPP", "+96879665522")

UTM_SOURCE = "linkedin"
UTM_MEDIUM = "social"

# Canonical paths, keyed by short name. "home" is the bare host.
# NOTE: there is deliberately NO "careers" key — the platform has no /careers
# route. Deleting it means any caller that still references it fails loudly
# (KeyError) instead of silently linking to a 404.
PATHS = {
    "home": "",
    "demo": "/demo",
    "book": "/book",
    "sanad": "/sanad/assistant",
    "feasibility": "/feasibility-studio",
    "investors": "/investors",
    "partners": "/partners",
}

# Valid booking intents accepted by the /book route's `type` query param.
BOOK_TYPES = {"demo", "consultation", "partner"}


def url(key: str) -> str:
    """Fully-qualified canonical URL (with scheme), no tracking params."""
    return BASE + PATHS[key]


def display(key: str) -> str:
    """Human-readable URL without the scheme — brand mentions only, never a CTA."""
    return BRAND_HOST + PATHS[key]


def tracked(key: str, campaign: str, *, source: str = UTM_SOURCE, medium: str = UTM_MEDIUM) -> str:
    """Canonical URL with UTM params filled in (campaign already known)."""
    return f"{url(key)}?utm_source={source}&utm_medium={medium}&utm_campaign={campaign}"


def tracked_template(key: str, *, source: str = UTM_SOURCE, medium: str = UTM_MEDIUM) -> str:
    """Like tracked() but leaves a literal {campaign} placeholder for str.format()."""
    return f"{url(key)}?utm_source={source}&utm_medium={medium}&utm_campaign={{campaign}}"


def _validate_book_type(type_: str) -> None:
    if type_ not in BOOK_TYPES:
        raise ValueError(
            f"Invalid book type {type_!r}. Valid types: {sorted(BOOK_TYPES)}."
        )


def book(type_: str, campaign: str, *, source: str = UTM_SOURCE, medium: str = UTM_MEDIUM) -> str:
    """Clickable /book CTA URL for a booking intent, with UTM params.

    `type_` must be one of BOOK_TYPES ({"demo", "consultation", "partner"}).
    """
    _validate_book_type(type_)
    return (
        f"{url('book')}?type={type_}"
        f"&utm_source={source}&utm_medium={medium}&utm_campaign={campaign}"
    )


def book_template(type_: str, *, source: str = UTM_SOURCE, medium: str = UTM_MEDIUM) -> str:
    """Like book() but leaves a literal {campaign} placeholder for str.format()."""
    _validate_book_type(type_)
    return (
        f"{url('book')}?type={type_}"
        f"&utm_source={source}&utm_medium={medium}&utm_campaign={{campaign}}"
    )


def whatsapp(prefill: str | None = None) -> str:
    """Return a wa.me link for WHATSAPP number (clickable, RTL-safe).

    With prefill, appends ?text=... so the lead's first message is pre-written
    and you know the chat came from LinkedIn.
    """
    num = WHATSAPP.lstrip("+").replace(" ", "")
    base = f"https://wa.me/{num}"
    return f"{base}?text={quote(prefill)}" if prefill else base
