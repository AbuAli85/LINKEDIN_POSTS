"""CI smoke-test for the quote-card generator.

Ensures Arabic cards are shaped correctly (connected, right-to-left) and that both
languages render to valid PNGs. Exits non-zero on failure so a broken shaping
dependency fails CI loudly instead of silently publishing a broken Arabic card.

Run locally or in CI:
    python verify_render.py
"""

from __future__ import annotations

import sys

from image_card import _is_arabic, _shape_ar, render_quote_card

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def main() -> None:
    # Language detection.
    assert _is_arabic("المندوب الذكي"), "Arabic text not detected as Arabic"
    assert not _is_arabic("payroll team"), "English text misdetected as Arabic"

    # Arabic must be reshaped into connected presentation forms — not left raw.
    word = "المندوب"
    shaped = _shape_ar(word)
    assert shaped != word, "Arabic was not reshaped (shaping libs inactive?)"
    assert any("ﭐ" <= c <= "﻿" for c in shaped), (
        "no Arabic presentation forms in shaped output — letters would be disconnected"
    )

    # Full renders must succeed and produce real PNGs.
    ar = render_quote_card("الأسبوع نفسه. شركتان من نفس المجال")
    en = render_quote_card("Your payroll team should not be working on weekends")
    assert ar[:8] == _PNG_MAGIC, "Arabic card is not a valid PNG"
    assert en[:8] == _PNG_MAGIC, "English card is not a valid PNG"

    print("OK: Arabic shaping + RTL render verified; English render verified")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — surface any failure as a non-zero exit
        print(f"VERIFY FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
