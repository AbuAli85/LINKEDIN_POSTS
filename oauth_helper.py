"""Exchange an OAuth authorization code for a LinkedIn access token.

Usage:
    LINKEDIN_CLIENT_ID=... LINKEDIN_CLIENT_SECRET=... \
        python oauth_helper.py CODE [REDIRECT_URI]

Or pass --refresh to use a stored refresh token:
    LINKEDIN_CLIENT_ID=... LINKEDIN_CLIENT_SECRET=... \
        LINKEDIN_REFRESH_TOKEN=... python oauth_helper.py --refresh
"""

import json
import os
import sys

import requests

TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
DEFAULT_REDIRECT = "https://www.linkedin.com/developers/tools/oauth/redirect"


def _post_token(data: dict) -> dict:
    response = requests.post(
        TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if response.status_code != 200:
        body = response.text
        try:
            err = response.json()
            if err.get("error") == "invalid_client":
                raise SystemExit(
                    "LinkedIn returned invalid_client. Check that:\n"
                    "  - LINKEDIN_CLIENT_ID matches the Auth tab in your app\n"
                    "  - LINKEDIN_CLIENT_SECRET is current (regenerate if unsure)\n"
                    "  - Neither value has trailing whitespace or quotes\n"
                    "  - The required products are approved on the app\n"
                    f"Raw response: {body}"
                )
        except ValueError:
            pass
        raise SystemExit(f"Token endpoint error {response.status_code}: {body}")
    return response.json()


def exchange_code(code: str, redirect_uri: str) -> dict:
    client_id = (os.environ.get("LINKEDIN_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("LINKEDIN_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        raise SystemExit(
            "LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set."
        )
    return _post_token(
        {
            "grant_type": "authorization_code",
            "code": code.strip(),
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
    )


def refresh(refresh_token: str) -> dict:
    client_id = (os.environ.get("LINKEDIN_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("LINKEDIN_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        raise SystemExit(
            "LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set."
        )
    return _post_token(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token.strip(),
            "client_id": client_id,
            "client_secret": client_secret,
        }
    )


def try_refresh_access_token() -> str | None:
    """Best-effort refresh of the LinkedIn access token from LINKEDIN_REFRESH_TOKEN.

    Returns the new access token on success, or None if refresh isn't
    configured (no refresh token / client credentials) or the refresh call
    itself fails. Never raises — callers should fall back to their original
    401 handling rather than crashing the whole run over a refresh attempt.
    """
    refresh_token = (os.environ.get("LINKEDIN_REFRESH_TOKEN") or "").strip()
    client_id = (os.environ.get("LINKEDIN_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("LINKEDIN_CLIENT_SECRET") or "").strip()
    if not refresh_token or not client_id or not client_secret:
        return None
    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
    except requests.exceptions.RequestException as exc:
        print(f"WARNING: token refresh network error: {exc}")
        return None
    if response.status_code != 200:
        print(f"WARNING: token refresh failed HTTP {response.status_code}: {response.text[:200]}")
        return None
    return response.json().get("access_token")


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "--refresh":
        token = (os.environ.get("LINKEDIN_REFRESH_TOKEN") or "").strip()
        if not token:
            raise SystemExit("LINKEDIN_REFRESH_TOKEN must be set for --refresh.")
        result = refresh(token)
    elif len(argv) >= 2:
        code = argv[1]
        redirect = argv[2] if len(argv) >= 3 else DEFAULT_REDIRECT
        result = exchange_code(code, redirect)
    else:
        print(__doc__, file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
