"""Render a branded 1080×1350 SmartPRO quote-card PNG for LinkedIn image posts.

Reproduces the brand "OG card" (smartpro-hub1/client/public/linkedin-quote-idea.svg):
dark-green gradient, soft glow circles, full-height accent bar, SmartPRO HUB wordmark,
oversized quotation mark, blockquote bar, auto-wrapped quote with an accent-colored
closing line, divider, attribution block, and a centered profile watermark. Only two
brand colors are used — #1c7811 (green) and #f43a35 (red) — varied per post as green,
red, or mixed (chosen from the post text). `pillar` is accepted only for API compat.

Arabic quotes are auto-detected and rendered right-to-left with proper letter
shaping (arabic-reshaper + python-bidi) using the bundled IBM Plex Sans Arabic, with a
fully mirrored layout. Other fonts fall back to common system fonts, then to
Pillow's built-in bitmap font.

CLI smoke-test:
    python -m image_card            # writes quote_card_sample.png (English)
    python image_card.py ar         # writes an Arabic sample card
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

# Bundled OFL fonts ship beside this module so rendering is identical everywhere.
_FONTS_DIR = Path(__file__).resolve().parent / "fonts"

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

# Arabic-capable fonts: bundled IBM Plex Sans Arabic first (always present, full
# presentation-form coverage), then OS fallbacks. A subsetted font drops glyphs
# (renders tofu), so the bundled copy is the reliable default.
_FONT_AR_CANDIDATES = [
    str(_FONTS_DIR / "IBMPlexSansArabic-Bold.ttf"),
    str(_FONTS_DIR / "IBMPlexSansArabic-Regular.ttf"),
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
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


def _load_font(size: int, arabic: bool = False):
    from PIL import ImageFont
    for path in (_FONT_AR_CANDIDATES if arabic else _FONT_CANDIDATES):
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    # Pillow built-in bitmap font — always available, looks coarse at large sizes
    return ImageFont.load_default()


def _is_arabic(text: str) -> bool:
    """True if the text contains Arabic-script characters."""
    return any(
        "؀" <= ch <= "ۿ" or "ݐ" <= ch <= "ݿ"
        or "ﭐ" <= ch <= "﷿" or "ﹰ" <= ch <= "﻿"
        for ch in text
    )


def _shape_ar(text: str) -> str:
    """Reshape + bidi-reorder Arabic so Pillow draws connected, right-to-left glyphs.

    Pillow has no built-in shaping, so without this Arabic renders as isolated,
    left-to-right letters. Falls back to the raw text if the libs are missing.
    """
    try:
        import arabic_reshaper
        try:
            from bidi.algorithm import get_display   # python-bidi < 0.5
        except Exception:
            from bidi import get_display             # python-bidi >= 0.5
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def _best_quote(text: str) -> str:
    """Return the first non-empty line under 200 chars (stripped of trailing period)."""
    for line in text.split("\n"):
        line = line.strip()
        if line and len(line) < 200:
            return line.rstrip(".")
    return (text[:196] + " ...") if len(text) > 200 else text


def _wrap_to_width(draw, text: str, font, max_width: int, measure=None) -> list[str]:
    """Word-wrap `text` so each line's *rendered* width stays within `max_width`.

    Measures each candidate line with the actual font (not a character count), so
    a long bold line can never render wider than the card and clip off the edge.
    `measure` maps a logical string to the glyphs actually drawn (e.g. Arabic
    shaping) so width reflects what the reader sees; the returned lines stay
    logical and the caller re-applies `measure` when drawing. A single word wider
    than `max_width` is hard-split so it can never overflow.
    """
    render = measure or (lambda s: s)
    words = text.split()
    if not words:
        return [""]

    def fits(s: str) -> bool:
        return draw.textlength(render(s), font=font) <= max_width

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
    return lines


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
    quote  = _best_quote(text)

    # Arabic quotes drive a right-to-left, shaped, mirrored layout.
    rtl   = _is_arabic(quote)
    shape = _shape_ar if rtl else (lambda s: s)
    if rtl:
        author  = os.environ.get("LINKEDIN_AUTHOR_AR", "فهد العامري")
        role    = os.environ.get("LINKEDIN_ROLE_AR", "المؤسس ورئيس مجلس الإدارة، سمارت برو")
        tagline = os.environ.get("LINKEDIN_TAGLINE_AR", "سلطنة عُمان")
    else:
        author  = os.environ.get("LINKEDIN_AUTHOR", "Fahad Al Amri")
        role    = os.environ.get("LINKEDIN_ROLE", "Founder & Chairman, SmartPRO Hub")
        tagline = "HUB · SULTANATE OF OMAN"

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

    # Full-height brand bar (mixes primary→accent2). On the right edge for RTL.
    bar_x0 = CARD_W - 14 if rtl else 0
    for yy in range(CARD_H):
        draw.line([(bar_x0, yy), (bar_x0 + 14, yy)],
                  fill=_blend(primary, accent2, yy / (CARD_H - 1)))

    # Wordmark: "Smart" (white) + "PRO" (accent2). The Latin brand stays LTR but
    # right-aligns on Arabic cards; the tagline follows the reading direction.
    font_brand = _load_font(46)
    font_tag   = _load_font(20, arabic=rtl)
    smart_w = draw.textlength("Smart", font=font_brand)
    pro_w   = draw.textlength("PRO", font=font_brand)
    if rtl:
        edge = CARD_W - 90
        draw.text((edge - pro_w - smart_w, 92), "Smart", font=font_brand, fill=TEXT_COLOR)
        draw.text((edge - pro_w, 92), "PRO", font=font_brand, fill=accent2)
        draw.text((edge, 148), shape(tagline), font=font_tag, fill=SUBTITLE_COL, anchor="ra")
        draw.text((CARD_W - 82, 235), "”", font=_load_font(180, arabic=True),
                  fill=dim_accent, anchor="ra")
    else:
        draw.text((90, 92), "Smart", font=font_brand, fill=TEXT_COLOR)
        draw.text((90 + smart_w, 92), "PRO", font=font_brand, fill=accent2)
        draw.text((92, 148), tagline, font=font_tag, fill=SUBTITLE_COL)
        draw.text((82, 235), "“", font=_load_font(180), fill=dim_accent)

    # Quote sits between the wordmark and the attribution block. Wrap by measured
    # pixel width and auto-shrink so it can never clip the right edge or bottom.
    area_top, area_bottom = 430, CARD_H - 215
    max_text_w = CARD_W - 132 - MARGIN     # text starts at x=132
    max_text_h = area_bottom - area_top
    size = QUOTE_SIZE
    while True:
        font_quote = _load_font(size, arabic=rtl)
        lines   = _wrap_to_width(draw, quote, font_quote, max_text_w, measure=shape)
        ascent, descent = font_quote.getmetrics()
        line_h  = ascent + descent + LINE_SPACING
        block_h = line_h * len(lines) - LINE_SPACING
        widest  = max(draw.textlength(shape(ln), font=font_quote) for ln in lines)
        if (widest <= max_text_w and block_h <= max_text_h) or size <= MIN_QUOTE_SIZE:
            break
        size -= 4

    y = area_top + max(0, (max_text_h - block_h) // 2)   # vertically centered in the area

    # Blockquote accent rule beside the quote (right of the text for RTL), then the
    # quote line by line so the closing line can be accented for emphasis.
    if rtl:
        text_x, rule_x, anchor = CARD_W - 132, CARD_W - 100, "ra"
    else:
        text_x, rule_x, anchor = 132, 92, "la"
    draw.rectangle([(rule_x, y - 4), (rule_x + 8, y + block_h + 4)], fill=accent)
    for i, ln in enumerate(lines):
        last = (i == len(lines) - 1 and len(lines) > 1)
        draw.text((text_x, y), shape(ln), font=font_quote,
                  fill=accent2 if last else TEXT_COLOR, anchor=anchor)
        y += line_h

    # Attribution block (divider + name + role) near the bottom; right-aligned for RTL.
    base_y = CARD_H - 170
    if rtl:
        ax = CARD_W - 132
        draw.rectangle([(ax - 64, base_y - 34), (ax, base_y - 29)], fill=accent)
        draw.text((ax, base_y), shape(author), font=_load_font(34, arabic=True),
                  fill=TEXT_COLOR, anchor="ra")
        draw.text((ax, base_y + 46), shape(role), font=_load_font(24, arabic=True),
                  fill=TITLE_COL, anchor="ra")
    else:
        draw.rectangle([(132, base_y - 34), (196, base_y - 29)], fill=accent)
        draw.text((132, base_y), author, font=_load_font(34), fill=TEXT_COLOR)
        draw.text((132, base_y + 46), role, font=_load_font(24), fill=TITLE_COL)

    # Handle watermark — centered along the bottom (URL stays LTR).
    draw.text((CARD_W // 2, CARD_H - 42), handle,
              font=_load_font(HANDLE_SIZE), fill=WATERMARK_COL, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


if __name__ == "__main__":
    import sys

    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "ar":
        sample = (
            "لماذا يعمل فريق الرواتب لديك في عطلة نهاية الأسبوع؟\n\n"
            "معظم شركات عُمان التي توظّف 20 إلى 50 موظفاً ما زالت تُدير الرواتب "
            "على جداول البيانات، ومع كل شهر تتكرر الأخطاء نفسها."
        )
    else:
        sample = (
            "Your payroll team should not be working on weekends.\n\n"
            "Most Oman businesses with 20–50 employees still run payroll on spreadsheets. "
            "Every month, the same mistakes. The same manual fixes. "
            "The same late-night calls when the bank rejects a WPS file."
        )
    data = render_quote_card(sample, post_index=1)
    out  = Path("quote_card_sample.png")
    out.write_bytes(data)
    print(f"Saved {out} ({len(data):,} bytes)")
