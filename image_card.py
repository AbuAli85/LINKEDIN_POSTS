"""Render a branded 1080×1350 quote-card PNG for LinkedIn image posts.

No external font files required — tries common system fonts in order and
falls back to Pillow's built-in bitmap font if none are found.

CLI smoke-test:
    python -m image_card            # writes quote_card_sample.png
    python image_card.py pain       # force a specific pillar accent
"""

from __future__ import annotations

import io
import os
from pathlib import Path

CARD_W, CARD_H   = 1080, 1350
BORDER_PX        = 6
BG_COLOR         = (10, 10, 10)
TEXT_COLOR       = (237, 233, 227)
MUTED_COLOR      = (110, 110, 110)
MARGIN           = 80
QUOTE_SIZE       = 52
MIN_QUOTE_SIZE   = 30   # auto-shrink floor when the quote is long
HANDLE_SIZE      = 18
LINE_SPACING     = 14

# Match the accent palette used in dashboard.py
PILLAR_COLOR: dict[str, str] = {
    "pain":       "#ef4444",
    "proof":      "#10b981",
    "leadership": "#3b82f6",
    "marketing":  "#f59e0b",
    "vision":     "#818cf8",
    "conversion": "#a855f7",
}
_DEFAULT_ACCENT = "#e8372a"

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


def _hex_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


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

    accent  = _hex_rgb(PILLAR_COLOR.get(pillar, _DEFAULT_ACCENT))
    handle  = os.environ.get("LINKEDIN_HANDLE", "linkedin.com/in/fahad-alamri-smartpro")
    quote   = _best_quote(text)

    img  = Image.new("RGB", (CARD_W, CARD_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Top accent border
    draw.rectangle([(0, 0), (CARD_W, BORDER_PX)], fill=accent)

    font_handle = _load_font(HANDLE_SIZE)

    # Fit the quote to the card: wrap by measured pixel width, and shrink the font
    # until the block fits both the usable width AND height (so nothing clips off
    # the right edge or the bottom). `rule_x = x - 22` needs ~22px of left gutter,
    # so the usable text width leaves room for the accent rule.
    max_text_w = CARD_W - 2 * MARGIN - 22
    max_text_h = CARD_H - (BORDER_PX + MARGIN) - 96   # reserve space for the handle
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

    # Centered — guaranteed within margins now that text_w <= usable width.
    x = max(MARGIN, (CARD_W - text_w) // 2)
    y = max(BORDER_PX + MARGIN, (CARD_H - text_h) // 2 - 24)

    # Thin vertical accent rule to the left of the quote
    rule_x = x - 22
    if rule_x >= MARGIN // 2:
        draw.rectangle(
            [(rule_x, y - 4), (rule_x + 3, y + text_h + 4)],
            fill=accent,
        )

    # Quote text
    draw.multiline_text(
        (x, y), wrapped,
        font=font_quote, fill=TEXT_COLOR,
        align="left", spacing=LINE_SPACING,
    )

    # Handle — bottom right
    draw.text(
        (CARD_W - MARGIN, CARD_H - 38),
        handle, font=font_handle, fill=MUTED_COLOR, anchor="rm",
    )

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
