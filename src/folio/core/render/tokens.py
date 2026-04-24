from __future__ import annotations

MM_TO_PT = 72 / 25.4
PT_TO_MM = 25.4 / 72

A4 = (210.0, 297.0)
A5 = (148.0, 210.0)
DL = (99.0, 210.0)
US_LETTER = (215.9, 279.4)
ROLLUP_850x2000 = (850.0, 2000.0)

A4_WIDTH_MM, A4_HEIGHT_MM = A4
A4_WIDTH_PT = round(A4_WIDTH_MM * MM_TO_PT, 2)
A4_HEIGHT_PT = round(A4_HEIGHT_MM * MM_TO_PT, 2)

DEFAULT_FONT_FAMILY = "Inter, 'Helvetica Neue', Arial, sans-serif"
MONO_FONT_FAMILY = "'JetBrains Mono', monospace"

WHITE = "#ffffff"
INK = "#0a1628"
INK_2 = "#1e2c44"
INK_3 = "#162b4e"
INK_4 = "#1f3a6a"
MUTED = "#5e6b82"
MUTED_LIGHT = "#8a99ac"
MUTED_SOFT = "#99a4b8"
TEXT_SOFT = "#d1d8e2"
LINE = "#d9dde6"
SOFT = "#f3f5f9"
ACCENT = "#c8a24a"
ACCENT_DARK = "#8f7223"
BLUE_GLOW = "#1e50a0"
