"""LinkedIn Ads reporting: fetch campaign analytics from a sponsored ad account.

Wraps the versioned Marketing API (`/rest/adAnalytics`, `/rest/adAccounts`) so you
can discover the ad accounts a token can see, list their campaigns, and pull
performance metrics for any of them.

This is separate from metrics.py, which tracks *organic* post engagement via
/v2/socialActions. Ads reporting needs the `r_ads_reporting` scope (plus `r_ads`
to enumerate accounts and campaigns) — an organic posting token will 403 here.

Reference: https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads-reporting/ads-reporting
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from atomic_io import write_json

API_BASE = "https://api.linkedin.com/rest"
HISTORY_DIR = Path(__file__).parent / "ad_analytics_history"

# LinkedIn versions the Marketing API by YYYYMM and sunsets old versions, so this
# is deliberately overridable without a code change when the current one ages out.
DEFAULT_VERSION = os.environ.get("LINKEDIN_API_VERSION", "202606")

# Only impressions and clicks come back unless `fields` is set explicitly.
# LinkedIn caps a request at 20 metrics.
DEFAULT_METRICS = [
    "dateRange",
    "pivotValues",
    "impressions",
    "clicks",
    "landingPageClicks",
    "costInLocalCurrency",
    "externalWebsiteConversions",
    "reactions",
    "shares",
]

# Analytics Finder groups by exactly one pivot.
PIVOTS = [
    "ACCOUNT", "CAMPAIGN", "CAMPAIGN_GROUP", "CREATIVE", "COMPANY", "SHARE",
    "CONVERSION", "SERVING_LOCATION", "CARD_INDEX", "PLACEMENT_NAME",
    "IMPRESSION_DEVICE_TYPE", "EVENT_STAGE",
    "MEMBER_COMPANY", "MEMBER_COMPANY_SIZE", "MEMBER_INDUSTRY",
    "MEMBER_SENIORITY", "MEMBER_JOB_TITLE", "MEMBER_JOB_FUNCTION",
    "MEMBER_COUNTRY_V2", "MEMBER_REGION_V2",
]

TIME_GRANULARITIES = ["ALL", "DAILY", "MONTHLY", "YEARLY"]

# Documented failure modes, mapped to what the caller should actually do about them.
ERROR_HINTS = {
    400: "Bad request — check pivot, timeGranularity and that dateRange.start precedes dateRange.end.",
    401: "Token missing, expired or invalid. Re-run OAuth.",
    403: "Not authorized — the token needs r_ads_reporting and the user needs access to this account/campaign.",
    404: "Not found — verify the account or campaign ID.",
    414: "Request URL too long. Narrow --metrics, or use query tunneling.",
    429: "Throttled — over 45M metric values in a 5-minute window. Request fewer metrics or a shorter range.",
    500: "LinkedIn server error. Retry.",
    503: "LinkedIn under maintenance. Retry shortly.",
}


class LinkedInAdsError(RuntimeError):
    """An Ads API call failed in a way the caller can't paper over."""


# ---------------------------------------------------------------------------
# Rest.li 2.0 request plumbing
# ---------------------------------------------------------------------------

def _token() -> str:
    """Ads reporting usually needs its own token, so prefer a dedicated one."""
    token = (
        os.environ.get("LINKEDIN_ADS_ACCESS_TOKEN")
        or os.environ.get("LINKEDIN_ACCESS_TOKEN")
        or ""
    ).strip()
    if not token:
        raise LinkedInAdsError(
            "No token found. Set LINKEDIN_ADS_ACCESS_TOKEN (or LINKEDIN_ACCESS_TOKEN)."
        )
    return token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_token()}",
        "LinkedIn-Version": DEFAULT_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _get(path: str, query: str) -> dict:
    """GET with a hand-built Rest.li query string.

    The query is appended raw rather than passed through requests' params=, because
    Rest.li needs literal parens/commas in `dateRange=(start:(...))` and
    `List(...)` while the URNs inside them must stay percent-encoded. Letting
    requests encode the whole thing breaks the syntax and returns 400.
    """
    url = f"{API_BASE}{path}?{query}"
    try:
        resp = requests.get(url, headers=_headers(), timeout=30)
    except requests.RequestException as exc:
        raise LinkedInAdsError(f"Request to {path} failed: {exc}") from exc

    if resp.status_code != 200:
        hint = ERROR_HINTS.get(resp.status_code, "")
        raise LinkedInAdsError(
            f"{path} returned {resp.status_code}. {hint}\n  {resp.text[:300]}"
        )
    return resp.json()


def _urn_list(param: str, urns: list[str]) -> str:
    """Encode a facet as `param=List(urn%3Ali%3A...)` — colons encoded, parens literal."""
    encoded = ",".join(u.replace(":", "%3A") for u in urns)
    return f"{param}=List({encoded})"


def _date_range(start: date, end: date | None) -> str:
    """Encode a Rest.li DateRange. Both bounds are inclusive; end defaults to today."""
    out = f"dateRange=(start:(year:{start.year},month:{start.month},day:{start.day})"
    if end:
        out += f",end:(year:{end.year},month:{end.month},day:{end.day})"
    return out + ")"


def _campaign_urn(campaign: str) -> str:
    """Accept a bare campaign ID or a full URN."""
    campaign = str(campaign).strip()
    return campaign if campaign.startswith("urn:li:") else f"urn:li:sponsoredCampaign:{campaign}"


def _account_urn(account: str) -> str:
    account = str(account).strip()
    return account if account.startswith("urn:li:") else f"urn:li:sponsoredAccount:{account}"


def _account_id(account: str) -> str:
    """The adAccounts sub-resources take a bare numeric ID, not a URN."""
    return str(account).strip().rsplit(":", 1)[-1]


# ---------------------------------------------------------------------------
# Discovery: which accounts and campaigns can this token see?
# ---------------------------------------------------------------------------

def list_ad_accounts(status: str = "ACTIVE", include_test: bool = False) -> list[dict]:
    """Return every ad account the authenticated user can access.

    Follows cursor pagination (pageToken/nextPageToken) to the end.
    """
    accounts: list[dict] = []
    page_token = None
    while True:
        search = f"(status:(values:List({status})),test:{str(include_test).lower()})"
        query = f"q=search&search={search}&pageSize=100"
        if page_token:
            query += f"&pageToken={page_token}"
        data = _get("/adAccounts", query)
        accounts.extend(data.get("elements", []))
        page_token = (data.get("metadata") or {}).get("nextPageToken")
        if not page_token:
            break
    return accounts


def list_campaigns(account: str, status: str = "ACTIVE", include_test: bool = False) -> list[dict]:
    """Return the campaigns under one ad account."""
    campaigns: list[dict] = []
    page_token = None
    while True:
        search = f"(status:(values:List({status})),test:{str(include_test).lower()})"
        query = f"q=search&search={search}&pageSize=100"
        if page_token:
            query += f"&pageToken={page_token}"
        data = _get(f"/adAccounts/{_account_id(account)}/adCampaigns", query)
        campaigns.extend(data.get("elements", []))
        page_token = (data.get("metadata") or {}).get("nextPageToken")
        if not page_token:
            break
    return campaigns


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def fetch_campaign_analytics(
    *,
    campaigns: list[str] | None = None,
    account: str | None = None,
    start: date,
    end: date | None = None,
    pivot: str = "CAMPAIGN",
    granularity: str = "DAILY",
    metrics: list[str] | None = None,
) -> list[dict]:
    """Pull analytics rows for specific campaigns, or for a whole ad account.

    Exactly one facet is needed: pass `campaigns` for named campaigns, or
    `account` to cover everything in the account. Returns the raw `elements`
    rows with derived rates attached to each.
    """
    if pivot not in PIVOTS:
        raise LinkedInAdsError(f"Unknown pivot {pivot!r}. Valid: {', '.join(PIVOTS)}")
    if granularity not in TIME_GRANULARITIES:
        raise LinkedInAdsError(
            f"Unknown timeGranularity {granularity!r}. Valid: {', '.join(TIME_GRANULARITIES)}"
        )
    if not campaigns and not account:
        raise LinkedInAdsError("Pass either campaigns=[...] or account=... as the facet.")

    metrics = metrics or DEFAULT_METRICS
    if len(metrics) > 20:
        raise LinkedInAdsError(f"LinkedIn allows at most 20 metrics per request, got {len(metrics)}.")

    parts = [
        "q=analytics",
        f"pivot={pivot}",
        f"timeGranularity={granularity}",
        _date_range(start, end),
    ]
    if campaigns:
        parts.append(_urn_list("campaigns", [_campaign_urn(c) for c in campaigns]))
    else:
        parts.append(_urn_list("accounts", [_account_urn(account)]))
    parts.append("fields=" + ",".join(metrics))

    data = _get("/adAnalytics", "&".join(parts))
    return [_with_derived_rates(row) for row in data.get("elements", [])]


def _with_derived_rates(row: dict) -> dict:
    """Attach CTR / CPC / CPM / conversion rate — LinkedIn returns only raw counts."""
    impressions = row.get("impressions") or 0
    clicks = row.get("clicks") or 0
    conversions = row.get("externalWebsiteConversions") or 0
    try:
        cost = float(row.get("costInLocalCurrency") or 0)
    except (TypeError, ValueError):
        cost = 0.0

    derived = {}
    if impressions:
        derived["ctr_pct"] = round(clicks / impressions * 100, 3)
        derived["cpm"] = round(cost / impressions * 1000, 2)
    if clicks:
        derived["cpc"] = round(cost / clicks, 2)
        derived["conversion_rate_pct"] = round(conversions / clicks * 100, 2)
    if conversions:
        derived["cost_per_conversion"] = round(cost / conversions, 2)

    return {**row, "derived": derived}


def summarize(rows: list[dict]) -> dict:
    """Roll daily/pivoted rows up into one set of totals.

    Rates are recomputed from the summed counts rather than averaged, because
    averaging per-row rates over-weights low-volume days.
    """
    totals = {"impressions": 0, "clicks": 0, "landingPageClicks": 0,
              "externalWebsiteConversions": 0, "reactions": 0, "shares": 0}
    cost = 0.0
    for row in rows:
        for key in totals:
            totals[key] += row.get(key) or 0
        try:
            cost += float(row.get("costInLocalCurrency") or 0)
        except (TypeError, ValueError):
            pass

    summary = {**totals, "cost": round(cost, 2), "rows": len(rows)}
    summary.update(_with_derived_rates({**totals, "costInLocalCurrency": cost})["derived"])
    return summary


def save_report(rows: list[dict], summary: dict, label: str) -> Path:
    """Persist a report to ad_analytics_history/ for trend comparison later."""
    HISTORY_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
    path = HISTORY_DIR / f"{stamp}_{safe}.json"
    write_json(path, {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "api_version": DEFAULT_VERSION,
        "summary": summary,
        "elements": rows,
    })
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise SystemExit(f"Invalid date {value!r} — use YYYY-MM-DD.")


def _print_rows(rows: list[dict]) -> None:
    for row in rows:
        span = row.get("dateRange") or {}
        start = span.get("start") or {}
        when = (
            f"{start.get('year')}-{start.get('month'):02d}-{start.get('day'):02d}"
            if start.get("year") else "all-time"
        )
        pivot_value = ", ".join(row.get("pivotValues") or []) or "-"
        d = row.get("derived", {})
        print(
            f"  {when}  {pivot_value}\n"
            f"    impressions={row.get('impressions', 0)}  clicks={row.get('clicks', 0)}"
            f"  cost={row.get('costInLocalCurrency', '0')}"
            f"  conversions={row.get('externalWebsiteConversions', 0)}\n"
            f"    ctr={d.get('ctr_pct', '-')}%  cpc={d.get('cpc', '-')}  cpm={d.get('cpm', '-')}"
        )


def check_scope() -> None:
    """Diagnose whether the current token can actually read ads reporting."""
    try:
        accounts = list_ad_accounts()
    except LinkedInAdsError as exc:
        print(f"FAIL: {exc}")
        print("      Ads reporting needs r_ads (account access) and r_ads_reporting (analytics).")
        return
    print(f"OK: token can see {len(accounts)} active ad account(s).")
    for acct in accounts[:5]:
        print(f"  {acct.get('id')}  {acct.get('name')}  ({acct.get('currency')})")


def _cli() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn Ads campaign analytics.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("accounts", help="List ad accounts this token can access.")

    p_camp = sub.add_parser("campaigns", help="List campaigns under an ad account.")
    p_camp.add_argument("account", help="Ad account ID or sponsoredAccount URN.")
    p_camp.add_argument("--status", default="ACTIVE", help="Campaign status filter (default ACTIVE).")

    p_fetch = sub.add_parser("fetch", help="Fetch analytics for campaigns or a whole account.")
    p_fetch.add_argument("--campaign", action="append", dest="campaigns",
                         help="Campaign ID or URN. Repeat for several.")
    p_fetch.add_argument("--account", help="Ad account ID or URN — reports on the whole account.")
    p_fetch.add_argument("--start", help="Start date YYYY-MM-DD (default: 30 days ago).")
    p_fetch.add_argument("--end", help="End date YYYY-MM-DD (default: today).")
    p_fetch.add_argument("--pivot", default="CAMPAIGN", choices=PIVOTS, help="Grouping (default CAMPAIGN).")
    p_fetch.add_argument("--granularity", default="DAILY", choices=TIME_GRANULARITIES,
                         help="Time bucket (default DAILY).")
    p_fetch.add_argument("--metrics", help="Comma-separated metric list (max 20).")
    p_fetch.add_argument("--save", action="store_true", help="Write the report to ad_analytics_history/.")
    p_fetch.add_argument("--json", action="store_true", dest="as_json", help="Print raw JSON.")

    sub.add_parser("check-scope", help="Check whether the token has ads reporting access.")

    args = parser.parse_args()

    try:
        if args.cmd == "accounts":
            accounts = list_ad_accounts()
            if not accounts:
                print("No active ad accounts visible to this token.")
                return
            for acct in accounts:
                print(f"{acct.get('id')}\t{acct.get('name')}\t{acct.get('currency')}\t"
                      f"{','.join(acct.get('servingStatuses') or [])}")

        elif args.cmd == "campaigns":
            campaigns = list_campaigns(args.account, status=args.status)
            if not campaigns:
                print(f"No {args.status} campaigns in account {args.account}.")
                return
            for c in campaigns:
                print(f"{c.get('id')}\t{c.get('name')}\t{c.get('type')}\t{c.get('status')}")

        elif args.cmd == "fetch":
            start = _parse_date(args.start) if args.start else date.today() - timedelta(days=30)
            end = _parse_date(args.end) if args.end else None
            metrics = [m.strip() for m in args.metrics.split(",")] if args.metrics else None

            rows = fetch_campaign_analytics(
                campaigns=args.campaigns,
                account=args.account,
                start=start,
                end=end,
                pivot=args.pivot,
                granularity=args.granularity,
                metrics=metrics,
            )
            if not rows:
                print("No data — the campaign had no activity in this range, "
                      "or the token can't read this account.")
                return

            summary = summarize(rows)
            if args.as_json:
                print(json.dumps({"summary": summary, "elements": rows}, indent=2))
            else:
                label = ", ".join(args.campaigns) if args.campaigns else args.account
                print(f"{label}  {start} → {end or 'today'}  pivot={args.pivot}  ({args.granularity})\n")
                _print_rows(rows)
                print(f"\nTotals over {summary['rows']} row(s): "
                      f"impressions={summary['impressions']}  clicks={summary['clicks']}  "
                      f"cost={summary['cost']}  conversions={summary['externalWebsiteConversions']}  "
                      f"ctr={summary.get('ctr_pct', '-')}%  cpc={summary.get('cpc', '-')}")

            if args.save:
                label = "_".join(args.campaigns) if args.campaigns else str(args.account)
                print(f"\nSaved to {save_report(rows, summary, label)}")

        elif args.cmd == "check-scope":
            check_scope()

    except LinkedInAdsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    _cli()
