"""Design tokens re-exported for the public DSL.

Exposes the Folio color palette, page presets (``A4``, ``A5``, ``US_LETTER``,
``DL``, ``ROLLUP_850x2000``), font families, unit conversion factors, and a
``STYLES`` namespace of preset :class:`TextStyle` presets. Use via
``tokens.ACCENT``, ``tokens.STYLES.hero``, ``tokens.A4_WIDTH_MM``, etc.

Example:
    tokens.ACCENT

Tags: tokens, style
"""

from __future__ import annotations

from types import SimpleNamespace

from folio.core.dsl.styles import TextStyle
from folio.core.render import tokens as render_tokens
from folio.core.render.tokens import (
    A4,
    A4_HEIGHT_MM,
    A4_HEIGHT_PT,
    A4_WIDTH_MM,
    A4_WIDTH_PT,
    A5,
    ACCENT,
    ACCENT_DARK,
    BLUE_GLOW,
    DEFAULT_FONT_FAMILY,
    DL,
    INK,
    INK_2,
    INK_3,
    INK_4,
    LINE,
    MM_TO_PT,
    MONO_FONT_FAMILY,
    MUTED,
    MUTED_LIGHT,
    MUTED_SOFT,
    PT_TO_MM,
    SOFT,
    TEXT_SOFT,
    US_LETTER,
    WHITE,
    ROLLUP_850x2000,
)

hero = TextStyle(font_size_pt=38, font_weight=800, fill=WHITE, letter_spacing=-0.95)
hero_subtitle = TextStyle(
    font_size_pt=11.5,
    font_weight=300,
    fill=WHITE,
    fill_opacity=0.82,
)
kicker = TextStyle(font_size_pt=8, font_weight=700, fill=ACCENT, letter_spacing=2.9)
stat_value = TextStyle(font_size_pt=13, font_weight=700, fill=WHITE)
stat_detail = TextStyle(font_size_pt=6.8, font_weight=400, fill=MUTED_SOFT, letter_spacing=1.0)
feature_title = TextStyle(font_size_pt=9.5, font_weight=600, fill=WHITE)
feature_body = TextStyle(font_size_pt=8.5, font_weight=400, fill=TEXT_SOFT)
flow_label = TextStyle(font_size_pt=8, font_weight=700, fill=ACCENT_DARK, letter_spacing=1.8)
flow_body = TextStyle(font_size_pt=8.5, font_weight=400, fill=INK_2)
capture_title = TextStyle(font_size_pt=7, font_weight=700, fill=MUTED, letter_spacing=1.2)
capture_value = TextStyle(font_size_pt=9, font_weight=600, fill=INK)
capture_body = TextStyle(font_size_pt=7.5, font_weight=400, fill=INK_2)
audience_title = TextStyle(font_size_pt=9.5, font_weight=700, fill=ACCENT, letter_spacing=2.1)
audience_body = TextStyle(font_size_pt=8.5, font_weight=400, fill=TEXT_SOFT)
brand_name = TextStyle(font_size_pt=22, font_weight=800, fill=WHITE, letter_spacing=-0.6)
brand_tagline = TextStyle(font_size_pt=8.5, font_weight=700, fill=ACCENT, letter_spacing=2.4)
meta = TextStyle(font_size_pt=8, font_weight=400, fill=MUTED_LIGHT, letter_spacing=1.0)
counter_mono = TextStyle(
    font_size_pt=8,
    font_weight=400,
    fill=MUTED,
    letter_spacing=1.1,
    font_family=MONO_FONT_FAMILY,
)
bottom_claim = TextStyle(font_size_pt=11, font_weight=500, fill=WHITE)

body = TextStyle(font_size_pt=8.5, font_weight=400, fill=INK_2)
body_large = TextStyle(font_size_pt=10.5, font_weight=300, fill=INK_2)
caption = stat_detail
page_title = TextStyle(font_size_pt=14, font_weight=800, fill=INK, letter_spacing=-0.2)
section_label = TextStyle(font_size_pt=7.5, font_weight=700, fill=ACCENT_DARK, letter_spacing=2.1)
title = TextStyle(font_size_pt=9.5, font_weight=600)
title_large = page_title

_extensions: dict[str, str] = {}


def extend(**colors: str) -> None:
    """Register additional color tokens on :mod:`folio.dsl.tokens`.

    Each keyword becomes a new attribute on both :mod:`folio.dsl.tokens` and
    :mod:`folio.render.tokens` so the renderer picks up custom palette
    colors.

    Args:
        colors: Name/value pairs, where each value is a CSS color string.

    Example:
        tokens.extend(BRAND_GOLD='#c8a24a')

    Tags: tokens, extension
    """
    for name, value in colors.items():
        _extensions[name] = value
        globals()[name] = value
        setattr(render_tokens, name, value)


def __getattr__(name: str) -> str:
    try:
        return _extensions[name]
    except KeyError as exc:
        raise AttributeError(
            f"module 'folio.dsl.tokens' has no attribute {name!r}"
        ) from exc


def __dir__() -> list[str]:
    return sorted({*globals(), *_extensions})


STYLES = SimpleNamespace(
    hero=hero,
    hero_subtitle=hero_subtitle,
    kicker=kicker,
    stat_value=stat_value,
    stat_detail=stat_detail,
    feature_title=feature_title,
    feature_body=feature_body,
    flow_label=flow_label,
    flow_body=flow_body,
    capture_title=capture_title,
    capture_value=capture_value,
    capture_body=capture_body,
    audience_title=audience_title,
    audience_body=audience_body,
    brand_name=brand_name,
    brand_tagline=brand_tagline,
    meta=meta,
    counter_mono=counter_mono,
    bottom_claim=bottom_claim,
    body=body,
    body_large=body_large,
    caption=caption,
    page_title=page_title,
    section_label=section_label,
    title=title,
    title_large=title_large,
    BODY=body,
    BODY_LG=body_large,
    CAPTION=caption,
    DISPLAY=hero,
    KICKER=kicker,
    LABEL=section_label,
    LEAD=hero_subtitle,
    META=meta,
    META_MONO=counter_mono,
    STAT_VALUE=stat_value,
    TITLE=title,
    TITLE_LG=title_large,
)

__all__ = [
    "A4",
    "A4_HEIGHT_MM",
    "A4_HEIGHT_PT",
    "A4_WIDTH_MM",
    "A4_WIDTH_PT",
    "A5",
    "ACCENT",
    "ACCENT_DARK",
    "BLUE_GLOW",
    "DEFAULT_FONT_FAMILY",
    "DL",
    "INK",
    "INK_2",
    "INK_3",
    "INK_4",
    "LINE",
    "MM_TO_PT",
    "MONO_FONT_FAMILY",
    "MUTED",
    "MUTED_LIGHT",
    "MUTED_SOFT",
    "PT_TO_MM",
    "ROLLUP_850x2000",
    "SOFT",
    "STYLES",
    "TEXT_SOFT",
    "TextStyle",
    "US_LETTER",
    "WHITE",
    "extend",
]
