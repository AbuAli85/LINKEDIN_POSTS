"""Audience-aware strategy module loader.

Reads LINKEDIN_AUDIENCE env var and returns the matching strategy module.
Backwards-compatible: when LINKEDIN_AUDIENCE is unset or 'personal',
returns content_strategy unchanged — so the existing personal pipeline
behaves exactly as before.

Usage:
    from strategy_loader import load_strategy
    s = load_strategy()
    s.PILLARS, s.HASHTAGS, s.pick_pillar, ...

Or for one-off use in a function:
    from strategy_loader import load_strategy
    pick_pillar = load_strategy().pick_pillar
"""

import importlib
import os
from pathlib import Path

PERSONAL_HISTORY_DIR = Path(__file__).parent / "posts_history"
COMPANY_HISTORY_DIR  = Path(__file__).parent / "company_posts_history"

VALID_AUDIENCES = {"personal", "company"}


def get_audience() -> str:
    """Return the active audience: 'personal' (default) or 'company'."""
    raw = (os.environ.get("LINKEDIN_AUDIENCE") or "personal").strip().lower()
    if raw not in VALID_AUDIENCES:
        raise ValueError(
            f"Invalid LINKEDIN_AUDIENCE={raw!r}. "
            f"Must be one of: {sorted(VALID_AUDIENCES)}"
        )
    return raw


def load_strategy():
    """Return the strategy module matching the active audience."""
    audience = get_audience()
    if audience == "company":
        return importlib.import_module("company_content_strategy")
    return importlib.import_module("content_strategy")


def history_dir() -> Path:
    """Return the posts_history directory for the active audience."""
    return COMPANY_HISTORY_DIR if get_audience() == "company" else PERSONAL_HISTORY_DIR


def author_urn_env_var() -> str:
    """Return the env var name holding the right author URN for this audience."""
    return "LINKEDIN_ORG_URN" if get_audience() == "company" else "LINKEDIN_AUTHOR_URN"


def access_token_env_var() -> str:
    """Return the env var name holding the right access token for this audience."""
    return "LINKEDIN_ORG_TOKEN" if get_audience() == "company" else "LINKEDIN_ACCESS_TOKEN"
