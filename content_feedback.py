"""Content performance feedback: track LinkedIn engagement over time, analyse pillar
performance, and store results in content_analysis.json for strategy tuning.

Commands:
  python content_feedback.py fetch-aged  # fetch metrics for posts 7+ days old
  python content_feedback.py analyze     # analyse pillar/hook perf, write content_analysis.json
  python content_feedback.py report      # print human-readable performance report
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HISTORY_DIR   = Path(__file__).parent / "posts_history"
ANALYSIS_FILE = Path(__file__).parent / "content_analysis.json"
LEADS_CSV     = Path(__file__).parent / "leads.csv"

ARABIC_PILLARS = {"pain_ar", "sanad_pro_ar"}


# ---------------------------------------------------------------------------
# Hook style detection
# ---------------------------------------------------------------------------

def detect_hook_style(first_line: str) -> str:
    """Classify the hook style of a post's first line into one of 7 categories."""
    import re
    line = first_line.strip()
    lower = line.lower()

    # numbered-list: digit followed closely by a list count word, OR count-word pattern anywhere
    if re.match(r"^\d+\s+\w*\s*\b(ways|things|reasons|steps|signs)\b", lower):
        return "numbered-list"
    if re.search(r"\b\d+\s+\b(ways|things|reasons|steps|signs)\b", lower):
        return "numbered-list"

    # question: ends with ?
    if line.endswith("?"):
        return "question"

    # observation: specific first-person observation phrases (before generic story/data checks)
    if re.search(r"(i'?ve noticed|i noticed|i keep|something i|one thing|here'?s what)", lower):
        return "observation"

    # story: first-person or time markers
    if re.search(r"\b(i |we |last |yesterday)\b", lower):
        return "story"

    # data-lead: statistic at start, or digit with financial/time unit
    if re.match(r"^\d", line):
        return "data-lead"
    if re.search(r"\b\d+\s*(%|omr|\$|hours?|minutes?|days?)\b", lower):
        return "data-lead"
    if re.search(r"(omr|%|\$)\s*\d+", lower):
        return "data-lead"

    # story: past tense in first 4 words (after digit-start check to avoid adjectives like "licensed")
    first_words = lower.split()[:4]
    if any(w.endswith("ed") for w in first_words):
        return "story"

    # contrast: adversative markers
    if re.search(r"\b(but|yet|however)\b", lower):
        return "contrast"
    if re.search(r"(everyone says|most people|conventional)", lower):
        return "contrast"

    # fallback
    return "bold-statement"


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


def _load_leads() -> list[dict]:
    """Read leads.csv; return [] if absent or unreadable."""
    if not LEADS_CSV.exists():
        return []
    try:
        with LEADS_CSV.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    except Exception:
        return []


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

        # Auto-tag hook_style if not already set (English pillars only)
        if post.get("pillar") in ARABIC_PILLARS:
            continue
        try:
            post = _load(f)  # reload after potential fetch update
            metrics = post.get("metrics") or {}
            if metrics.get("hook_style"):
                continue
            post_text = post.get("post", "")
            if not post_text:
                continue
            first_line = post_text.strip().split("\n")[0]
            style = detect_hook_style(first_line)
            metrics["hook_style"] = style
            post["metrics"] = metrics
            _save(f, post)
            print(f"hook_style auto-tagged: {style} for {f.name}")
        except Exception:
            pass

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

    # ── Demo conversion correlation ─────────────────────────────────────────
    # Reads leads.csv; correlates post_topic → post pillar → demo outcome.
    # Only meaningful once demo_outcome / demo_requested columns are filled in.
    demo_analysis: dict = {}
    leads = _load_leads()
    if leads:
        # Map post_topic fragment → pillar via posts_history
        topic_to_pillar: dict[str, str] = {}
        for f in HISTORY_DIR.glob("*.json"):
            try:
                p = _load(f)
                if t := p.get("topic"):
                    topic_to_pillar[t.lower()[:60]] = p.get("pillar", "unknown")
            except Exception:
                continue

        pillar_leads: dict[str, int]     = defaultdict(int)
        pillar_demos: dict[str, int]     = defaultdict(int)
        pillar_converted: dict[str, int] = defaultdict(int)
        pillar_value: dict[str, float]   = defaultdict(float)
        total_demos = total_converted = 0

        for row in leads:
            intent = row.get("intent", "")
            if intent not in ("high", "medium"):
                continue
            topic_key = (row.get("post_topic") or "").lower()[:60]
            pillar    = topic_to_pillar.get(topic_key, "unknown")
            pillar_leads[pillar] += 1

            if row.get("demo_requested") == "yes":
                pillar_demos[pillar] += 1
                total_demos += 1

            outcome = row.get("demo_outcome", "")
            if outcome == "converted":
                pillar_converted[pillar] += 1
                total_converted += 1
                try:
                    pillar_value[pillar] += float(row.get("deal_value") or 0)
                except ValueError:
                    pass

        if pillar_leads:
            demo_analysis = {
                "total_qualified_leads": sum(pillar_leads.values()),
                "total_demos":           total_demos,
                "total_converted":       total_converted,
                "per_pillar": {
                    p: {
                        "leads":       pillar_leads[p],
                        "demos":       pillar_demos.get(p, 0),
                        "converted":   pillar_converted.get(p, 0),
                        "deal_value_omr": round(pillar_value.get(p, 0.0), 2),
                        "demo_rate":   round(pillar_demos.get(p, 0) / pillar_leads[p], 3),
                        "close_rate":  round(pillar_converted.get(p, 0) / max(pillar_demos.get(p, 1), 1), 3),
                    }
                    for p in pillar_leads
                },
            }

    analysis = {
        "generated_at":          datetime.now(timezone.utc).isoformat(),
        "total_posts_analyzed":   len(posts),
        "pillar_performance":     pillar_summary,
        "hook_performance":       hook_summary,
        "frequency_multipliers":  frequency_multipliers,
        "best_pillar":            best_pillar,
        "best_hook_style":        best_hook,
        "recommended_emphasis":   ranked_pillars,
        "demo_pipeline":          demo_analysis,
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

    dp = a.get("demo_pipeline", {})
    if dp and dp.get("total_qualified_leads", 0) > 0:
        print(f"\n{'─'*55}")
        print(f" Demo Pipeline  "
              f"(leads={dp['total_qualified_leads']}  demos={dp['total_demos']}  "
              f"converted={dp['total_converted']})")
        pp2 = dp.get("per_pillar", {})
        if pp2:
            print(f"\n {'Pillar':<14} {'Leads':>6}  {'Demos':>5}  {'Demo%':>6}  {'Close%':>7}  {'OMR':>8}")
            print(" " + "-" * 52)
            for pillar, d in sorted(pp2.items(), key=lambda x: -x[1]["converted"]):
                print(f"  {pillar:<13} {d['leads']:>6}  {d['demos']:>5}  "
                      f"{d['demo_rate']*100:>5.1f}%  {d['close_rate']*100:>6.1f}%  "
                      f"{d['deal_value_omr']:>8.0f}")
        if dp["total_qualified_leads"] > 0 and dp["total_demos"] == 0:
            print("\n  (No demo_requested=yes entries yet — fill in leads.csv to see conversion data)")
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
