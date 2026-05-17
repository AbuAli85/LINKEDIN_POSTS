"""Generate the SmartPro weekly newsletter using Claude.

Pulls the last week of LinkedIn posts (Pain / Proof / Vision / Leadership /
Marketing) and synthesizes them — plus one tactical playbook and one
discussion prompt — into a single weekly issue.

Same pattern as generator.py: draft → save JSON to newsletter_history/ →
dashboard renders for approve → newsletter_publisher.py sends via Resend.

Run:
    python newsletter.py            # draft this week's issue
    python newsletter.py --print    # also print the issue body to stdout
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from content_strategy import BRAND_URL, COMPANY_CTA

ROOT             = Path(__file__).parent
POSTS_DIR        = ROOT / "posts_history"
NEWSLETTER_DIR   = ROOT / "newsletter_history"
NEWSLETTER_DIR.mkdir(exist_ok=True)

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS    = 2400

SYSTEM_PROMPT = """You are an elite B2B newsletter editor writing for HR managers
and SME founders in Oman. Your readers run companies with 10-200 employees and
deal with payroll, WPS, leave, and Ministry of Labour compliance every week.

VOICE
- Direct, specific, lived-in. You sound like a peer who's been in their seat.
- One concrete number or detail per claim. Never generic.
- Short paragraphs. Real white space. Never a wall of text.
- Warm but not folksy. No corporate jargon.

STRUCTURE (every issue follows this shape)
1. SUBJECT LINE — 6-10 words, plain English, no clickbait. Specific enough that
   a busy HR manager opens it on a Tuesday morning.
2. PREVIEW TEXT — the inbox sub-line, 80-120 chars. Hook the open.
3. OPENING — 2-3 short paragraphs. One sharp observation about the week in
   Oman business. Personal, present tense, no fluff.
4. THIS WEEK'S PAIN — 1-2 paragraphs naming a real, specific operational pain
   most Oman SMBs feel. Use a number if you have one. Tie subtly to SmartPro.
5. THIS WEEK'S PROOF — 1 paragraph: a concrete result a SmartPro customer got.
   Numbers, before/after, anonymized but real.
6. THE PLAYBOOK — a 4-6 step actionable how-to the reader can run THIS WEEK
   even if they're not a customer. Genuinely useful, not gated.
7. ONE QUESTION — a single open question that invites a reply. Real curiosity.
8. SIGN-OFF — short, by name, with a clear CTA to www.thesmartpro.io.

TERMINOLOGY (use these exact English terms — never the wrong alternative)
- Ministry of Labour  (NOT "Ministry of Manpower" — the ministry was renamed)
- Wages Protection System / WPS  (NOT "salary protection", "payroll system")
- Social Protection Fund / SPF  (NOT "PASI", "social insurance authority")
- Omanization  (NOT "localization", "Omanisation" with an 's')
- work permit  (NOT "work authorisation", "work licence")
- end-of-service gratuity  (NOT "end-of-service bonus", "severance pay")

BANNED
- "In today's fast-paced world", "delve", "tapestry", "game-changer", "unlock"
- Hashtags (this isn't social — it's email)
- Emojis in section bodies (one is fine in a section header at most)
- Empty openers like "Hope you're having a great week"

OUTPUT FORMAT
Return a single JSON object with these keys:
{
  "subject":      string,
  "preview":      string,
  "opening":      string (markdown ok, real \\n line breaks),
  "pain":         {"title": string, "body": string},
  "proof":        {"title": string, "body": string},
  "playbook":     {"title": string, "steps": [string, string, ...]},
  "question":     string,
  "signoff":      string
}

No preamble, no code fences. Just the JSON."""


USER_TEMPLATE = """Draft this week's SmartPro newsletter issue.

ISSUE NUMBER: {issue_num}
ISSUE DATE:   {issue_date}
AUDIENCE:     HR managers and founders running 10-200 person companies in Oman.

BRAND CONTEXT
SmartPro is an end-to-end HR, payroll, and operations platform for Oman
businesses. It handles WPS submission with direct bank integration, leave and
attendance, and Ministry of Labour compliance — all in one place. Buyers are
business owners, HR managers, and finance managers. Most are stuck running HR
on spreadsheets and WhatsApp threads. The newsletter exists to build trust and
generate demos.

CTA URL: {brand_url}
DEMO CTA (use a softened version in the signoff): {cta_line}

RECENT LINKEDIN POSTS (last week — use as raw material, but DON'T copy whole
sentences; mine for themes, pain points, and proof numbers):
{recent_posts}

Now draft the JSON object."""


def _load_recent_posts(limit: int = 8) -> list[dict]:
    """Return the most recent published/approved LinkedIn posts."""
    files = sorted(POSTS_DIR.glob("*.json"), reverse=True)[:limit]
    out = []
    for f in files:
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
            out.append(p)
        except Exception:
            continue
    return out


def _format_recent_posts(posts: list[dict]) -> str:
    if not posts:
        return "(no recent posts — synthesize from brand context only)"
    lines = []
    for p in posts[:6]:
        pillar = (p.get("pillar") or "post").upper()
        topic  = (p.get("topic") or "(no topic)").strip()
        body   = (p.get("post") or "").strip()
        # Trim to a representative snippet so the prompt stays reasonable.
        snippet = (body[:600] + "…") if len(body) > 600 else body
        lines.append(f"[{pillar}] {topic}\n{snippet}\n")
    return "\n".join(lines)


def _recent_newsletter_topics(n: int = 5) -> list[str]:
    """Return subject + summary strings for the last n newsletter issues, oldest first."""
    files = sorted(NEWSLETTER_DIR.glob("*.json"))[-n:]
    topics: list[str] = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            subject = data.get("subject") or data.get("title") or ""
            summary = data.get("summary") or data.get("preview") or ""
            if subject:
                topics.append(f"Issue subject: {subject} | Summary: {summary[:120]}")
        except Exception:
            pass
    return topics


_STOP_WORDS = frozenset({
    "a", "an", "the", "your", "our", "is", "are", "was", "were",
    "in", "on", "at", "to", "of", "and", "or", "for", "with",
    "that", "it", "its", "this", "how", "what", "why", "when", "will", "won",
})


def _subject_too_similar(
    new_subject: str,
    recent_topics: list[str],
    threshold: float = 0.6,
) -> bool:
    """True if new_subject shares ≥ threshold of its keywords with any recent subject."""
    def keywords(s: str) -> set[str]:
        return {w.lower() for w in s.split() if w.lower() not in _STOP_WORDS and len(w) > 3}

    new_kw = keywords(new_subject)
    if not new_kw:
        return False
    for recent in recent_topics:
        subject_part = recent.split("|")[0].replace("Issue subject:", "").strip()
        recent_kw = keywords(subject_part)
        if not recent_kw:
            continue
        if len(new_kw & recent_kw) / len(new_kw) >= threshold:
            return True
    return False


def _next_issue_number() -> int:
    existing = list(NEWSLETTER_DIR.glob("issue_*.json"))
    if not existing:
        return 1
    nums = []
    for f in existing:
        try:
            nums.append(int(f.stem.split("_", 2)[1]))
        except Exception:
            continue
    return (max(nums) + 1) if nums else 1


def _parse_json_response(text: str) -> dict:
    """Be forgiving about minor preamble/code-fence noise."""
    t = text.strip()
    if t.startswith("```"):
        # strip fenced block
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
        t = t.strip("`\n ")
    # Find the first { and last } to bound the JSON
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output")
    return json.loads(t[start : end + 1])


def generate_issue(model: str = DEFAULT_MODEL) -> dict:
    """Draft a new newsletter issue and persist it as JSON.

    Returns the parsed issue dict (with metadata)."""
    client = anthropic.Anthropic()
    issue_num   = _next_issue_number()
    issue_date  = datetime.now(timezone.utc).date().isoformat()
    recent      = _load_recent_posts()
    recent_nls  = _recent_newsletter_topics()

    if recent_nls:
        avoid_block = (
            "\n\nRECENT NEWSLETTER ISSUES (do NOT repeat these topics or frames):\n"
            + "\n".join(f"  - {t}" for t in recent_nls)
            + "\n\nChoose a completely different topic, angle, and subject line."
        )
    else:
        avoid_block = ""

    prompt = USER_TEMPLATE.format(
        issue_num=issue_num,
        issue_date=issue_date,
        brand_url=BRAND_URL,
        cta_line=COMPANY_CTA,
        recent_posts=_format_recent_posts(recent),
    ) + avoid_block

    resp = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    issue = _parse_json_response(raw)

    # Post-generation subject uniqueness check — regenerate once if too similar
    if recent_nls and _subject_too_similar(issue.get("subject", ""), recent_nls):
        print(
            f"WARNING: Subject too similar to recent issues ({issue.get('subject')!r}). "
            "Regenerating with stronger avoid block…"
        )
        stronger = prompt + (
            "\n\nCRITICAL: The previous attempt produced a subject line too close to a "
            "recent issue. You MUST choose an entirely different angle, pain point, and "
            "framing. Avoid anything related to the topics listed above."
        )
        resp2 = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": stronger}],
        )
        raw2 = "".join(b.text for b in resp2.content if getattr(b, "type", None) == "text")
        try:
            issue2 = _parse_json_response(raw2)
            if _subject_too_similar(issue2.get("subject", ""), recent_nls):
                print(
                    f"WARNING: Second attempt still similar ({issue2.get('subject')!r}). "
                    "Proceeding anyway — review manually."
                )
            issue = issue2
        except Exception as e:
            print(f"WARNING: Second attempt failed to parse ({e}). Using first result.")

    # Attach metadata
    issue["_meta"] = {
        "issue_number": issue_num,
        "date":         issue_date,
        "model":        model,
        "status":       "draft",
        "source_posts": [p.get("_filename") or p.get("topic", "?") for p in recent],
        "created_at":   datetime.now(timezone.utc).isoformat(),
    }

    # Save
    fname = f"issue_{issue_num:03d}_{issue_date}.json"
    (NEWSLETTER_DIR / fname).write_text(
        json.dumps(issue, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Saved {fname}")
    return issue


def render_text(issue: dict) -> str:
    """Render a newsletter issue dict as a plain-text email body."""
    parts = [
        issue["opening"].strip(),
        "",
        "—",
        "",
        f"{issue['pain']['title'].upper()}",
        issue["pain"]["body"].strip(),
        "",
        f"{issue['proof']['title'].upper()}",
        issue["proof"]["body"].strip(),
        "",
        f"{issue['playbook']['title'].upper()}",
    ]
    for i, step in enumerate(issue["playbook"]["steps"], 1):
        parts.append(f"{i}. {step.strip()}")
    parts.extend([
        "",
        "—",
        "",
        issue["question"].strip(),
        "",
        issue["signoff"].strip(),
        "",
        f"Visit {BRAND_URL} · WhatsApp +96879665522",
    ])
    return "\n".join(parts)


def render_html(issue: dict) -> str:
    """Render a newsletter issue dict as a simple, email-safe HTML body."""
    import html as _html

    def esc(s):
        return _html.escape(s or "")

    def md_paras(s):
        # Two newlines = paragraph break.
        paras = [p.strip() for p in (s or "").split("\n\n") if p.strip()]
        return "\n".join(
            f'<p style="margin:0 0 14px;font-size:16px;line-height:1.6;color:#222">{esc(p).replace(chr(10), "<br>")}</p>'
            for p in paras
        )

    steps_html = "".join(
        f'<li style="margin:0 0 10px;font-size:16px;line-height:1.6;color:#222">{esc(s.strip())}</li>'
        for s in issue["playbook"]["steps"]
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{esc(issue['subject'])}</title></head>
<body style="margin:0;padding:0;background:#f5f5f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#222">
<div style="max-width:600px;margin:0 auto;padding:32px 24px;background:#ffffff">

  <div style="margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #eee">
    <div style="font-size:13px;color:#888;letter-spacing:1px;text-transform:uppercase">SmartPro Weekly</div>
    <div style="font-size:13px;color:#aaa">Issue #{issue['_meta']['issue_number']} · {issue['_meta']['date']}</div>
  </div>

  {md_paras(issue['opening'])}

  <h2 style="font-size:14px;letter-spacing:1px;text-transform:uppercase;color:#888;margin:32px 0 14px">{esc(issue['pain']['title'])}</h2>
  {md_paras(issue['pain']['body'])}

  <h2 style="font-size:14px;letter-spacing:1px;text-transform:uppercase;color:#888;margin:32px 0 14px">{esc(issue['proof']['title'])}</h2>
  {md_paras(issue['proof']['body'])}

  <h2 style="font-size:14px;letter-spacing:1px;text-transform:uppercase;color:#888;margin:32px 0 14px">{esc(issue['playbook']['title'])}</h2>
  <ol style="padding-left:20px;margin:0 0 14px">{steps_html}</ol>

  <hr style="border:none;border-top:1px solid #eee;margin:32px 0">

  {md_paras(issue['question'])}

  <p style="margin:24px 0 14px;font-size:16px;line-height:1.6;color:#222">{esc(issue['signoff'])}</p>

  <div style="margin-top:32px;padding-top:20px;border-top:1px solid #eee;font-size:13px;color:#888;text-align:center">
    SmartPro · Muscat, Oman · <a href="https://{BRAND_URL}/" style="color:#2a9a5c;text-decoration:none">{BRAND_URL}</a><br>
    <a href="https://wa.me/96879665522" style="color:#888;text-decoration:none">WhatsApp +968 7966 5522</a>
  </div>
</div>
</body></html>"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a SmartPro newsletter issue")
    parser.add_argument("--print", action="store_true", help="Print the issue body to stdout")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Anthropic model")
    args = parser.parse_args()

    issue = generate_issue(model=args.model)

    if args.print:
        print()
        print("=" * 70)
        print(f"SUBJECT: {issue['subject']}")
        print(f"PREVIEW: {issue['preview']}")
        print("=" * 70)
        print(render_text(issue))
