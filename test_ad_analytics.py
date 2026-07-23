"""Tests for LinkedIn Ads reporting query encoding and metric math.

The Rest.li 2.0 query syntax is the fragile part: parens and commas must stay
literal while URN colons must be percent-encoded. Get it wrong and every call
returns 400, so the expected strings below are copied from the samples in
https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads-reporting/ads-reporting
"""
from datetime import date

import pytest

import ad_analytics as aa


# ── Rest.li 2.0 encoding ────────────────────────────────────────────────────

def test_date_range_matches_documented_syntax():
    assert aa._date_range(date(2024, 1, 1), None) == "dateRange=(start:(year:2024,month:1,day:1))"
    assert aa._date_range(date(2024, 5, 28), date(2024, 9, 30)) == (
        "dateRange=(start:(year:2024,month:5,day:28),end:(year:2024,month:9,day:30))"
    )


def test_urn_list_encodes_colons_but_not_parens():
    encoded = aa._urn_list("campaigns", ["urn:li:sponsoredCampaign:1234567"])
    assert encoded == "campaigns=List(urn%3Ali%3AsponsoredCampaign%3A1234567)"
    assert "%28" not in encoded and "%29" not in encoded


def test_urn_list_joins_multiple_facets_with_literal_comma():
    encoded = aa._urn_list("accounts", ["urn:li:sponsoredAccount:1", "urn:li:sponsoredAccount:2"])
    assert encoded == "accounts=List(urn%3Ali%3AsponsoredAccount%3A1,urn%3Ali%3AsponsoredAccount%3A2)"


@pytest.mark.parametrize("given,expected", [
    ("1234567", "urn:li:sponsoredCampaign:1234567"),
    ("urn:li:sponsoredCampaign:1234567", "urn:li:sponsoredCampaign:1234567"),
])
def test_campaign_urn_accepts_bare_id_or_urn(given, expected):
    assert aa._campaign_urn(given) == expected


def test_account_id_strips_urn_prefix():
    assert aa._account_id("urn:li:sponsoredAccount:502840441") == "502840441"
    assert aa._account_id("502840441") == "502840441"


def test_request_url_matches_documented_sample(monkeypatch):
    captured = {}

    class _Resp:
        status_code = 200
        def json(self): return {"elements": []}

    monkeypatch.setenv("LINKEDIN_ADS_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(aa.requests, "get",
                        lambda url, **kw: (captured.update(url=url, **kw), _Resp())[1])

    aa.fetch_campaign_analytics(
        campaigns=["1234567"], start=date(2024, 1, 1),
        pivot="CREATIVE", granularity="ALL", metrics=["impressions"],
    )

    assert captured["url"] == (
        "https://api.linkedin.com/rest/adAnalytics?q=analytics&pivot=CREATIVE"
        "&timeGranularity=ALL&dateRange=(start:(year:2024,month:1,day:1))"
        "&campaigns=List(urn%3Ali%3AsponsoredCampaign%3A1234567)&fields=impressions"
    )
    assert captured["headers"]["X-Restli-Protocol-Version"] == "2.0.0"
    assert captured["headers"]["LinkedIn-Version"] == aa.DEFAULT_VERSION


# ── input validation ────────────────────────────────────────────────────────

def test_rejects_unknown_pivot_and_granularity(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ADS_ACCESS_TOKEN", "test-token")
    with pytest.raises(aa.LinkedInAdsError, match="Unknown pivot"):
        aa.fetch_campaign_analytics(campaigns=["1"], start=date(2026, 1, 1), pivot="HOURLY")
    with pytest.raises(aa.LinkedInAdsError, match="timeGranularity"):
        aa.fetch_campaign_analytics(campaigns=["1"], start=date(2026, 1, 1), granularity="WEEKLY")


def test_rejects_over_twenty_metrics(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ADS_ACCESS_TOKEN", "test-token")
    with pytest.raises(aa.LinkedInAdsError, match="at most 20 metrics"):
        aa.fetch_campaign_analytics(campaigns=["1"], start=date(2026, 1, 1),
                                    metrics=["impressions"] * 21)


def test_requires_a_facet(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ADS_ACCESS_TOKEN", "test-token")
    with pytest.raises(aa.LinkedInAdsError, match="facet"):
        aa.fetch_campaign_analytics(start=date(2026, 1, 1))


def test_missing_token_is_reported_clearly(monkeypatch):
    monkeypatch.delenv("LINKEDIN_ADS_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)
    with pytest.raises(aa.LinkedInAdsError, match="No token found"):
        aa._headers()


def test_http_error_carries_actionable_hint(monkeypatch):
    class _Resp:
        status_code = 403
        text = '{"message":"Not enough permissions"}'

    monkeypatch.setenv("LINKEDIN_ADS_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(aa.requests, "get", lambda url, **kw: _Resp())
    with pytest.raises(aa.LinkedInAdsError, match="r_ads_reporting"):
        aa.list_ad_accounts()


# ── derived metrics ─────────────────────────────────────────────────────────

def test_derived_rates():
    derived = aa._with_derived_rates({
        "impressions": 10000, "clicks": 50,
        "costInLocalCurrency": "125.0", "externalWebsiteConversions": 5,
    })["derived"]
    assert derived["ctr_pct"] == 0.5
    assert derived["cpc"] == 2.5
    assert derived["cpm"] == 12.5
    assert derived["conversion_rate_pct"] == 10.0
    assert derived["cost_per_conversion"] == 25.0


def test_derived_rates_skip_division_by_zero():
    assert aa._with_derived_rates({"impressions": 0, "clicks": 0})["derived"] == {}


def test_summarize_recomputes_rates_from_totals_not_row_averages():
    # Row-averaged CTR would be (10% + 0.1%)/2 = 5.05%; the correct volume-weighted
    # answer is 11/10010 = 0.11%.
    summary = aa.summarize([
        {"impressions": 10, "clicks": 1, "costInLocalCurrency": "1.0"},
        {"impressions": 10000, "clicks": 10, "costInLocalCurrency": "20.0"},
    ])
    assert summary["impressions"] == 10010
    assert summary["clicks"] == 11
    assert summary["cost"] == 21.0
    assert summary["ctr_pct"] == 0.11
    assert summary["rows"] == 2


def test_summarize_tolerates_missing_and_malformed_cost():
    summary = aa.summarize([{"impressions": 5}, {"clicks": 1, "costInLocalCurrency": "n/a"}])
    assert summary["cost"] == 0.0
    assert summary["impressions"] == 5
