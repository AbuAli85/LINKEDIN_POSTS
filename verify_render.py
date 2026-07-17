"""CI smoke-test for the quote-card generator.

Ensures Arabic cards are shaped correctly (connected, right-to-left) and that both
languages render to valid PNGs. Exits non-zero on failure so a broken shaping
setup fails CI loudly instead of silently publishing a broken Arabic card.

The card relies on Pillow's native libraqm shaping for Arabic: the raw logical
string is drawn with direction="rtl"/language="ar" and libraqm joins letters and
applies the bidi algorithm. The previous arabic-reshaper + python-bidi pre-shaping
path rendered reversed, disconnected glyphs, so this test now treats a missing
libraqm as a hard failure rather than checking for legacy presentation forms.

Run locally or in CI:
    python verify_render.py
"""

from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont, features

from image_card import _has_raqm, _is_arabic, _load_font, render_quote_card

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# Arabic test fixtures (kept as escapes so the source stays ASCII-safe).
_AR_BRAND = "المندوب الذكي"   # "the smart delegate"
_AR_WORD  = "المندوب"                                   # "delegate"
_AR_QUOTE = ("الأسبوع نفسه. "
             "شركتان من نفس المجال")


def _report_versions() -> None:
    import importlib.metadata as md
    for pkg in ("pillow", "arabic-reshaper", "python-bidi"):
        try:
            print(f"  {pkg}=={md.version(pkg)}")
        except Exception:
            print(f"  {pkg}==<not installed>")
    print(f"  libraqm(raqm)=={'yes' if features.check('raqm') else 'NO'}")


def _ink_columns(text: str, font) -> int:
    """Render `text` natively (rtl) and count image columns containing ink.

    Connected Arabic fills a contiguous run of columns; disconnected or failed
    shaping leaves large gaps or far fewer inked columns. A coarse but real visual
    check that shaping actually happened (the old test never looked at pixels)."""
    img = Image.new("L", (1400, 160), 0)
    d = ImageDraw.Draw(img)
    d.text((1380, 30), text, font=font, fill=255, anchor="ra",
           direction="rtl", language="ar")
    px = img.load()
    return sum(1 for x in range(img.width)
               if any(px[x, y] for y in range(img.height)))


def main() -> None:
    print("Installed shaping deps:")
    _report_versions()

    # The card's correct path needs libraqm. Treat its absence as a hard failure
    # so a wheel without raqm can't silently fall back to broken Arabic.
    assert _has_raqm(), (
        "Pillow has no libraqm -- native Arabic shaping unavailable. Install a "
        "Pillow wheel built with raqm (PyPI wheels include it)."
    )

    # Language detection.
    assert _is_arabic(_AR_BRAND), "Arabic text not detected as Arabic"
    assert not _is_arabic("payroll team"), "English text misdetected as Arabic"

    # An Arabic-capable TrueType font must actually load (not the bitmap fallback).
    font = _load_font(80, arabic=True)
    assert isinstance(font, ImageFont.FreeTypeFont), (
        "No Arabic TrueType font loaded -- would render as boxes/garbage"
    )

    # Visual sanity: a short connected Arabic word should ink a healthy run of
    # columns. A near-empty result means shaping or the font failed.
    cols = _ink_columns(_AR_WORD, font)
    print(f"native rtl render of test word inked {cols} columns")
    assert cols > 120, f"Arabic render looks empty/broken (only {cols} inked columns)"

    # Full renders must succeed and produce real PNGs.
    ar = render_quote_card(_AR_QUOTE)
    en = render_quote_card("Your payroll team should not be working on weekends")
    assert ar[:8] == _PNG_MAGIC, "Arabic card is not a valid PNG"
    assert en[:8] == _PNG_MAGIC, "English card is not a valid PNG"

    print("OK: libraqm present; Arabic shaping + RTL render verified; English render verified")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 -- surface any failure as a non-zero exit
        msg = f"VERIFY FAILED: {exc}"
        print(msg, file=sys.stderr)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            try:
                import importlib.metadata as md
                with open(summary, "a", encoding="utf-8") as fh:
                    fh.write(f"### Card render self-test failed\n\n```\n{msg}\n")
                    for pkg in ("pillow", "arabic-reshaper", "python-bidi"):
                        try:
                            fh.write(f"{pkg}=={md.version(pkg)}\n")
                        except Exception:
                            fh.write(f"{pkg}==<not installed>\n")
                    fh.write(f"libraqm(raqm)=={'yes' if features.check('raqm') else 'NO'}\n")
                    fh.write("```\n")
            except Exception:
                pass
        sys.exit(1)
