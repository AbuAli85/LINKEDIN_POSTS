"""Content performance feedback: track LinkedIn engagement over time, analyse pillar
performance, and store results in content_analysis.json for strategy tuning.

Commands:
  python content_feedback.py fetch-aged  # fetch metrics for posts 7+ days old
  python content_feedback.py analyze     # analyse pillar/hook perf, write content_analysis.json
  python content_feedback.py report      # print human-readable performance report
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HISTORY_DIR   = Path(__file__).parent / "posts_history"
ANALYSIS_FILE = Path(__file__).parent / "content_analysis.json"


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _is_aged(post: dict, days: int = 7) -> bool:
    pub_at = post.get("published_at") or post.get("generated_at", "")
    if not pub_at:
        return False
    try:
        dt = datetime.fromisoformat(pub_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days >= days
    except Exception:
        return False


def _engagement_rate(metrics: dict) -> float:
    """Weighted engagement: (reactions + comments*3 + shares*5) / estimated_impressions.
    Impressions estimated as reactions * 50 (rough baseline when no impression data available).
    """
    r = int(metrics.get("reactions", 0) or 0)
    c = int(metrics.get("comments",  0) or 0)
    s = int(metrics.get("shares",    0) or 0)
    impressions = max(r * 50, 1)
    return round((r + c * 3 + s * 5) / impressions, 4)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_fetch_aged() -> int:
    """Fetch LinkedIn metrics for published posts ≥7 days old that lack recent data."""
    from metrics import fetch_post as _fetch_post

    updated = 0
    for f in sorted(HISTORY_DIR.glob("*.json")):
        try:
            post = _load(f)
        except Exception:
            continue
        if not (post.get("published") and post.get("post_id") and _is_aged(post, days=7)):
            continue

        # Skip if metrics were updated within the last 48 h
        metrics   = post.get("metrics") or {}
        updated_at = metrics.get("updated_at", "")
        if updated_at:
            try:
                dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - dt) < timedelta(hours=48):
                    continue
            except Exception:
                pass

        if _fetch_post(f):
            updated += 1

    print(f"Fetched metrics for {updated} post(s).")
    return updated


def cmd_analyze() -> dict:
    """Analyse pillar & hook performance; write content_analysis.json."""
    posts = []
    for f in HISTORY_DIR.glob("*.json"):
        try:
            p = _load(f)
            if p.get("published") and p.get("metrics"):
                posts.append(p)
        except Exception:
            continue

    if len(posts) < 3:
        print("Not enough published posts with metrics yet (need at least 3).")
        return {}

    pillar_data: dict[str, dict] = defaultdict(lambda: {
        "posts": 0, "reactions": 0, "comments": 0, "shares": 0, "engagement_rates": [],
    })
    hook_data: dict[str, list[float]] = defaultdict(list)

    for p in posts:
        pillar  = p.get("pillar", "unknown")
        metrics = p.get("metrics", {})
        er      = _engagement_rate(metrics)

        d = pillar_data[pillar]
        d["posts"]    += 1
        d["reactions"] += int(metrics.get("reactions", 0) or 0)
        d["comments"]  += int(metrics.get("comments",  0) or 0)
        d["shares"]    += int(metrics.get("shares",    0) or 0)
        d["engagement_rates"].append(er)

        if hs := (metrics.get("hook_style") or ""):
            hook_data[hs].append(er)

    # Pillar summary
    pillar_summary: dict[str, dict] = {}
    for pillar, d in pillar_data.items():
        n = d["posts"]
        avg_er = round(sum(d["engagement_rates"]) / n, 4) if n else 0.0
        pillar_summary[pillar] = {
            "posts":               n,
            "total_reactions":     d["reactions"],
            "total_comments":      d["comments"],
            "total_shares":        d["shares"],
            "avg_engagement_rate": avg_er,
        }

    # Hook summary
    hook_summary = {
        hs: round(sum(rates) / len(rates), 4)
        for hs, rates in hook_data.items() if rates
    }

    # Frequency multipliers: best pillar → 3.0x, worst → 1.0x (linear scale)
    ers = {p: v["avg_engagement_rate"] for p, v in pillar_summary.items()}
    max_er = max(ers.values()) if ers else 1.0
    frequency_multipliers = {
        p: round(1.0 + 2.0 * (er / max(max_er, 0.0001)), 2)
        for p, er in ers.items()
    }

    best_pillar    = max(ers, key=ers.get) if ers else None
    best_hook      = max(hook_summary, key=hook_summary.get) if hook_summary else None
    ranked_pillars = sorted(pillar_summary, key=lambda p: pillar_summary[p]["avg_engagement_rate"],
                            reverse=True)

    analysis = {
        "generated_at":          datetime.now(timezone.utc).isoformat(),
        "total_posts_analyzed":   len(posts),
        "pillar_performance":     pillar_summary,
        "hook_performance":       hook_summary,
        "frequency_multipliers":  frequency_multipliers,
        "best_pillar":            best_pillar,
        "best_hook_style":        best_hook,
        "recommended_emphasis":   ranked_pillars,
    }

    _save(ANALYSIS_FILE, analysis)
    print(f"Analysis saved → {ANALYSIS_FILE}  ({len(posts)} posts, {len(pillar_summary)} pillars)")
    return analysis


def cmd_report() -> None:
    """Print a human-readable performance report from content_analysis.json."""
    if not ANALYSIS_FILE.exists():
        print("No analysis file found. Run: python content_feedback.py analyze")
        return

    a  = _load(ANALYSIS_FILE)
    ts = a.get("generated_at", "unknown")[:19].replace("T", " ")

    print(f"\n{'='*55}")
    print(f" SmartPro Content Performance Report  {ts}")
    print(f"{'='*55}")
    print(f" Posts analysed : {a.get('total_posts_analyzed', 0)}")

    pp = a.get("pillar_performance", {})
    if pp:
        print(f"\n{'Pillar':<14} {'Posts':>5}  {'AvgER':>7}  {'React':>6}  {'Cmts':>5}  {'Shares':>6}")
        print("-" * 55)
        for pillar in a.get("recommended_emphasis", list(pp)):
            d = pp.get(pillar, {})
            print(f" {pillar:<13} {d.get('posts',0):>5}  {d.get('avg_engagement_rate',0):>7.4f}"
                  f"  {d.get('total_reactions',0):>6}  {d.get('total_comments',0):>5}"
                  f"  {d.get('total_shares',0):>6}")

    if bp := a.get("best_pillar"):
        print(f"\n Best performing pillar : {bp}")
    if bh := a.get("best_hook_style"):
        print(f" Best hook style        : {bh}")

    if fm := a.get("frequency_multipliers"):
        print(f"\n{'Frequency multipliers (generate more of top pillars)':}")
        for pillar, mult in sorted(fm.items(), key=lambda x: -x[1]):
            bar = "█" * int(mult * 4)
            print(f"  {pillar:<14} {mult:.2f}x  {bar}")

    if re := a.get("recommended_emphasis"):
        print(f"\n Recommended emphasis order: {' → '.join(re)}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Content performance analysis for SmartPro LinkedIn posts."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch-aged", help="Fetch metrics for posts 7+ days old")
    sub.add_parser("analyze",    help="Analyse pillar performance and write content_analysis.json")
    sub.add_parser("report",     help="Print human-readable performance report")

    args = parser.parse_args()
    {"fetch-aged": cmd_fetch_aged, "analyze": cmd_analyze, "report": cmd_report}[args.cmd]()


if __name__ == "__main__":
    _cli()
