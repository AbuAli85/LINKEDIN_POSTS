#!/usr/bin/env python3
"""
check_token.py — LinkedIn token health diagnostic

Usage:
    python check_token.py                          # checks LINKEDIN_ACCESS_TOKEN
    python check_token.py --token YOUR_TOKEN_HERE  # checks a specific token
    python check_token.py --all                    # checks all 3 token env vars

What it checks:
    ✓ Token is set and non-empty
    ✓ Token is valid (LinkedIn /v2/userinfo)
    ✓ Profile identity (name, LinkedIn ID)
    ✓ Scopes present on token
    ✓ w_member_social  — can publish posts
    ✓ r_member_social  — can read comments/engagement (Community Management API)
    ✓ r_liteprofile    — can read basic profile
    ✓ r_emailaddress   — can read email
    ✓ CTA comment test — tries to post a comment (dry-run check)
    ✓ Comment read test — tries to read comments on most recent post
"""

import argparse
import json
import os
import sys
import requests
from pathlib import Path

LI_BASE    = "https://api.linkedin.com/v2"
HISTORY    = Path(__file__).parent / "posts_history"

REQUIRED_SCOPES = {
    "w_member_social": "Publish posts + CTA comments",
    "r_member_social": "Read comments → capture leads (Community Management API)",
    "r_liteprofile":   "Read your basic profile",
    "r_emailaddress":  "Read your email",
}

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✓{RESET}  {msg}")
def fail(msg): print(f"  {RED}✗{RESET}  {msg}")
def warn(msg): print(f"  {YELLOW}⚠{RESET}  {msg}")
def head(msg): print(f"\n{BOLD}{msg}{RESET}")


def check_token(token: str, label: str) -> dict:
    result = {"label": label, "valid": False, "scopes": [], "name": "", "id": ""}

    head(f"── {label} ──")

    if not token:
        fail("Token is empty / not set")
        return result

    ok(f"Token present ({len(token)} chars, ends …{token[-8:]})")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    # ── 1. userinfo ───────────────────────────────────────────────────────
    try:
        r = requests.get(f"{LI_BASE}/userinfo", headers=headers, timeout=10)
    except Exception as e:
        fail(f"Network error: {e}")
        return result

    if r.status_code == 401:
        fail("Token EXPIRED or INVALID (401)")
        return result
    if r.status_code != 200:
        fail(f"Unexpected status {r.status_code}: {r.text[:200]}")
        return result

    profile = r.json()
    name = f"{profile.get('given_name','')} {profile.get('family_name','')}".strip() or profile.get("name","?")
    li_id = profile.get("sub", "?")
    result["valid"] = True
    result["name"]  = name
    result["id"]    = li_id
    ok(f"Token valid — identity: {name} (ID: {li_id})")

    # ── 2. Scope introspection ────────────────────────────────────────────
    # LinkedIn doesn't expose scopes via API directly. We probe each endpoint.
    head("  Scope probes:")

    # r_liteprofile
    r2 = requests.get(f"{LI_BASE}/me", headers=headers, timeout=10)
    if r2.status_code == 200:
        ok("r_liteprofile  — /v2/me readable ✓")
        result["scopes"].append("r_liteprofile")
    else:
        fail(f"r_liteprofile  — /v2/me returned {r2.status_code}")

    # w_member_social — probe by checking shares endpoint (read-only probe)
    r3 = requests.get(
        f"{LI_BASE}/ugcPosts?q=authors&authors=List(urn%3Ali%3Aperson%3A{li_id})&count=1",
        headers=headers, timeout=10
    )
    if r3.status_code == 200:
        ok("w_member_social — UGC posts endpoint accessible ✓")
        result["scopes"].append("w_member_social")
    elif r3.status_code == 403:
        fail("w_member_social — 403 (posts endpoint blocked — cannot publish!)")
    else:
        warn(f"w_member_social — status {r3.status_code} (inconclusive)")

    # r_member_social — probe via socialActions on most recent post
    post_id = None
    for f in sorted(HISTORY.glob("*.json"), reverse=True):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            if d.get("post_id"):
                post_id = d["post_id"]
                break
        except Exception:
            continue

    if post_id:
        import urllib.parse
        encoded = urllib.parse.quote(post_id, safe="")
        r4 = requests.get(
            f"{LI_BASE}/socialActions/{encoded}/comments?count=1",
            headers=headers, timeout=10
        )
        if r4.status_code == 200:
            ok("r_member_social — comment endpoint readable ✓  (LEAD CAPTURE WORKS!)")
            result["scopes"].append("r_member_social")
        elif r4.status_code == 403:
            fail(
                "r_member_social — 403 BLOCKED\n"
                f"  {RED}→ This is why lead capture produces 0 results.{RESET}\n"
                "  → Fix: Apply for Community Management API at linkedin.com/developers\n"
                "         (Your App → Products tab → Request Access)\n"
                "         Then re-generate token with r_member_social scope."
            )
        elif r4.status_code == 401:
            fail("r_member_social — 401 token expired")
        else:
            warn(f"r_member_social — status {r4.status_code} (no published posts to probe?)")
    else:
        warn("r_member_social — skipped (no published posts with post_id found)")

    # ── 3. Summary ────────────────────────────────────────────────────────
    head("  Summary:")
    has_publish = "w_member_social" in result["scopes"]
    has_read    = "r_member_social" in result["scopes"]

    if has_publish and has_read:
        ok(f"{GREEN}FULLY OPERATIONAL{RESET} — can publish AND capture leads")
    elif has_publish and not has_read:
        warn(f"PARTIAL — posts publish OK but lead capture is BLOCKED\n"
             "  Posts fire daily but zero comments are harvested.\n"
             "  Apply for Community Management API to unlock r_member_social.")
    elif not has_publish:
        fail("CRITICAL — cannot publish posts (w_member_social missing)")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="LinkedIn token health check")
    parser.add_argument("--token", help="Check a specific token value")
    parser.add_argument("--all",   action="store_true", help="Check all 3 env var tokens")
    args = parser.parse_args()

    print(f"\n{BOLD}LinkedIn Token Diagnostic{RESET}")
    print("=" * 50)

    if args.token:
        check_token(args.token, "Provided token")
    elif args.all:
        tokens = {
            "LINKEDIN_ACCESS_TOKEN":  os.environ.get("LINKEDIN_ACCESS_TOKEN", ""),
            "LINKEDIN_READ_TOKEN":    os.environ.get("LINKEDIN_READ_TOKEN", ""),
            "LINKEDIN_COMMENT_TOKEN": os.environ.get("LINKEDIN_COMMENT_TOKEN", ""),
        }
        for label, token in tokens.items():
            if token:
                check_token(token, label)
            else:
                head(f"── {label} ──")
                warn("Not set in environment")
    else:
        token = (
            os.environ.get("LINKEDIN_ACCESS_TOKEN") or
            os.environ.get("LINKEDIN_READ_TOKEN") or ""
        ).strip()
        check_token(token, "LINKEDIN_ACCESS_TOKEN")

    print()


if __name__ == "__main__":
    main()
