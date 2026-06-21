"""Render a branded 1080×1350 SmartPRO quote-card PNG for LinkedIn image posts.

Reproduces the brand "OG card" (smartpro-hub1/client/public/linkedin-quote-idea.svg):
dark-green gradient, soft glow circles, full-height accent bar, SmartPRO HUB wordmark,
oversized quotation mark, blockquote bar, auto-wrapped quote with an accent-colored
closing line, divider, attribution block, and a centered profile watermark. Only two
brand colors are used — #1c7811 (green) and #f43a35 (red) — varied per post as green,
red, or mixed (chosen from the post text). `pillar` is accepted only for API compat.

No external font files required — tries common system fonts in order and
falls back to Pillow's built-in bitmap font if none are found.

CLI smoke-test:
    python -m image_card            # writes quote_card_sample.png
"""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path

CARD_W, CARD_H   = 1080, 1350

# Two-color brand palette — only these two accents ever appear on the card.
BRAND_GREEN      = (0x1c, 0x78, 0x11)   # #1c7811
BRAND_RED        = (0xf4, 0x3a, 0x35)   # #f43a35
TEXT_COLOR       = (0xff, 0xff, 0xff)   # quote + name
SUBTITLE_COL     = (0x9a, 0x9a, 0x9a)   # wordmark tagline (neutral grey)
TITLE_COL        = (0xb4, 0xb4, 0xb4)   # attribution role (neutral grey)
WATERMARK_COL    = (0x78, 0x78, 0x78)   # bottom handle (neutral grey)
MARGIN           = 80
QUOTE_SIZE       = 60
MIN_QUOTE_SIZE   = 32   # auto-shrink floor when the quote is long
HANDLE_SIZE      = 22
LINE_SPACING     = 16

# Each post uses one color variant, chosen from the post text so it stays stable
# per post yet varies across posts. Override with env LINKEDIN_CARD_VARIANT.
CARD_VARIANTS    = ("green", "red", "mixed")

# System font search — first found wins; uv/CI runner typically has DejaVu
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/calibri.ttf",
]


def _blend(c1, c2, t: float) -> tuple[int, int, int]:
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _pick_variant(seed: str) -> str:
    """Choose green / red / mixed — forced by env, else stable hash of the text."""
    forced = os.environ.get("LINKEDIN_CARD_VARIANT", "").strip().lower()
    if forced in CARD_VARIANTS:
        return forced
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    return CARD_VARIANTS[int(digest, 16) % len(CARD_VARIANTS)]


def _scheme(variant: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Return (primary, accent2) for a variant.

    `primary` drives the bars, glow, quote mark and divider; `accent2` colors the
    wordmark "PRO" and the quote's closing line. In "mixed" the two differ so both
    brand colors show; in single-color variants they are equal.
    """
    if variant == "red":
        return BRAND_RED, BRAND_RED
    if variant == "mixed":
        return BRAND_GREEN, BRAND_RED
    return BRAND_GREEN, BRAND_GREEN


def _load_font(size: int):
    from PIL import ImageFont
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    # Pillow built-in bitmap font — always available, looks coarse at large sizes
    return ImageFont.load_default()


def _best_quote(text: str) -> str:
    """Return the first non-empty line under 200 chars (stripped of trailing period)."""
    for line in text.split("\n"):
        line = line.strip()
        if line and len(line) < 200:
            return line.rstrip(".")
    return (text[:196] + " ...") if len(text) > 200 else text


def _wrap_to_width(draw, text: str, font, max_width: int) -> str:
    """Word-wrap `text` so each line's *rendered* width stays within `max_width`.

    Wrapping by character count (the previous approach) ignores the font, so at
    large bold sizes a "short" line could render wider than the card and clip off
    the right edge. This measures each candidate line with the actual font.
    A single word longer than `max_width` is hard-split so it can never overflow.
    """
    words = text.split()
    if not words:
        return ""

    def fits(s: str) -> bool:
        return draw.textlength(s, font=font) <= max_width

    lines: list[str] = []
    cur = ""
    for word in words:
        # Hard-split a word that alone exceeds the line width (e.g. a long URL).
        while not fits(word):
            cut = len(word)
            while cut > 1 and not fits(word[:cut]):
                cut -= 1
            if cut <= 1:
                break
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(word[:cut])
            word = word[cut:]
        trial = f"{cur} {word}".strip()
        if fits(trial):
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def render_quote_card(text: str, pillar: str = "", post_index: int = 0) -> bytes:
    """Render a 1080×1350 PNG and return raw PNG bytes.

    Args:
        text:       Full post body. The best single line is auto-selected as the quote.
        pillar:     Content pillar name — determines the accent color.
        post_index: Unused; reserved for future post-numbering overlays.
    """
    from PIL import Image, ImageDraw

    primary, accent2 = _scheme(_pick_variant(text))
    accent = primary  # bars, glow, quote mark and divider
    handle = os.environ.get("LINKEDIN_HANDLE", "linkedin.com/in/fahad-alamri-smartpro")
    author = os.environ.get("LINKEDIN_AUTHOR", "Fahad Al Amri")
    role   = os.environ.get("LINKEDIN_ROLE", "Founder & Chairman, SmartPRO Hub")
    quote  = _best_quote(text)

    # Very dark background, tinted toward the primary brand color.
    bg_top    = _blend(primary, (0, 0, 0), 0.88)
    bg_bottom = _blend(primary, (0, 0, 0), 0.94)

    # Vertical gradient background, built from a 1px column then stretched.
    column = Image.new("RGB", (1, CARD_H))
    for yy in range(CARD_H):
        column.putpixel((0, yy), _blend(bg_top, bg_bottom, yy / (CARD_H - 1)))
    img  = column.resize((CARD_W, CARD_H))

    # Soft brand glow circles (translucent) composited over the gradient.
    glow = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    gd.ellipse([980 - 380, 160 - 380, 980 + 380, 160 + 380], fill=(*primary, 20))   # ~0.08
    gd.ellipse([120 - 300, 1220 - 300, 120 + 300, 1220 + 300], fill=(*accent2, 15)) # ~0.06
    img  = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Dimmed accent (blend toward bg) for the oversized quote mark — avoids
    # needing an RGBA overlay just for one translucent glyph.
    dim_accent = _blend(bg_top, accent, 0.5)

    # Full-height brand bar on the left edge (mixes primary→accent2 top to bottom).
    for yy in range(CARD_H):
        draw.line([(0, yy), (14, yy)], fill=_blend(primary, accent2, yy / (CARD_H - 1)))

    # Wordmark: "Smart" (white) + "PRO" (accent) + tagline.
    font_brand = _load_font(46)
    font_tag   = _load_font(20)
    draw.text((90, 92), "Smart", font=font_brand, fill=TEXT_COLOR)
    smart_w = draw.textlength("Smart", font=font_brand)
    draw.text((90 + smart_w, 92), "PRO", font=font_brand, fill=accent2)
    draw.text((92, 148), "HUB · SULTANATE OF OMAN", font=font_tag, fill=SUBTITLE_COL)

    # Oversized decorative quotation mark.
    draw.text((82, 235), "“", font=_load_font(180), fill=dim_accent)

    # Quote sits between the wordmark and the attribution block. Wrap by measured
    # pixel width and auto-shrink so it can never clip the right edge or bottom.
    area_top, area_bottom = 430, CARD_H - 215
    max_text_w = CARD_W - 132 - MARGIN     # text starts at x=132
    max_text_h = area_bottom - area_top
    size = QUOTE_SIZE
    while True:
        font_quote = _load_font(size)
        wrapped = _wrap_to_width(draw, quote, font_quote, max_text_w)
        bbox    = draw.multiline_textbbox((0, 0), wrapped, font=font_quote, spacing=LINE_SPACING)
        text_w  = bbox[2] - bbox[0]
        text_h  = bbox[3] - bbox[1]
        if (text_w <= max_text_w and text_h <= max_text_h) or size <= MIN_QUOTE_SIZE:
            break
        size -= 4

    lines = wrapped.split("\n")
    ascent, descent = font_quote.getmetrics()
    line_h  = ascent + descent + LINE_SPACING
    block_h = line_h * len(lines) - LINE_SPACING
    x = 132
    y = area_top + max(0, (max_text_h - block_h) // 2)   # vertically centered in the area

    # Blockquote accent rule beside the quote, then the quote line by line so the
    # closing line can be accented for emphasis.
    draw.rectangle([(92, y - 4), (100, y + block_h + 4)], fill=accent)
    for i, ln in enumerate(lines):
        last = (i == len(lines) - 1 and len(lines) > 1)
        draw.text((x, y), ln, font=font_quote, fill=accent2 if last else TEXT_COLOR)
        y += line_h

    # Attribution block (divider + name + role) anchored near the bottom.
    base_y = CARD_H - 170
    draw.rectangle([(132, base_y - 34), (196, base_y - 29)], fill=accent)
    draw.text((132, base_y), author, font=_load_font(34), fill=TEXT_COLOR)
    draw.text((132, base_y + 46), role, font=_load_font(24), fill=TITLE_COL)

    # Handle watermark — centered along the bottom.
    draw.text((CARD_W // 2, CARD_H - 42), handle,
              font=_load_font(HANDLE_SIZE), fill=WATERMARK_COL, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


if __name__ == "__main__":
    import sys

    pillar_arg = sys.argv[1] if len(sys.argv) > 1 else "pain"
    sample = (
        "Your payroll team should not be working on weekends.\n\n"
        "Most Oman businesses with 20–50 employees still run payroll on spreadsheets. "
        "Every month, the same mistakes. The same manual fixes. "
        "The same late-night calls when the bank rejects a WPS file."
    )
    data = render_quote_card(sample, pillar=pillar_arg, post_index=1)
    out  = Path("quote_card_sample.png")
    out.write_bytes(data)
    print(f"Saved {out} ({len(data):,} bytes)  pillar={pillar_arg}")
