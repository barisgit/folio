from __future__ import annotations

from folio.dsl import TextStyle, tokens

tokens.extend(
    ink_black="#04060d",
    deep_navy="#080d1d",
    glass_navy="#18284a",
    mid_navy="#132243",
    coral="#ff5a3c",
    mist="#eef2f7",
    chalk="#f6f1e7",
)

PAGE_WIDTH_MM = 180.0
PAGE_HEIGHT_MM = 270.0

T = tokens.STYLES

DISPLAY_XL = TextStyle(
    font_size_pt=54,
    font_weight=800,
    fill=tokens.WHITE,
    letter_spacing=-2.0,
)
DISPLAY_XL_EM = TextStyle(
    font_size_pt=54,
    font_weight=800,
    fill=tokens.ACCENT,
    letter_spacing=-2.0,
    font_style="italic",
)
DISPLAY_SERIF = TextStyle(
    font_size_pt=54,
    font_weight=300,
    fill=tokens.WHITE,
    letter_spacing=-2.0,
    font_family="'Playfair Display', 'Iowan Old Style', Georgia, serif",
    font_style="italic",
)
GIANT_NUMBER = TextStyle(
    font_size_pt=320,
    font_weight=900,
    fill=tokens.ACCENT,
    fill_opacity=0.09,
    letter_spacing=-16.0,
)
EYEBROW = TextStyle(
    font_size_pt=7.8,
    font_weight=800,
    fill=tokens.ACCENT,
    letter_spacing=4.2,
)
EYEBROW_MUTED = TextStyle(
    font_size_pt=7.5,
    font_weight=700,
    fill=tokens.MUTED_LIGHT,
    letter_spacing=3.4,
)
LEDE = TextStyle(
    font_size_pt=11,
    font_weight=300,
    fill=tokens.WHITE,
    fill_opacity=0.8,
    letter_spacing=-0.05,
)
FEATURE_INDEX = TextStyle(
    font_size_pt=7,
    font_weight=800,
    fill=tokens.ACCENT,
    letter_spacing=2.4,
    font_family=tokens.MONO_FONT_FAMILY,
)
FEATURE_TAG = TextStyle(
    font_size_pt=7.5,
    font_weight=800,
    fill=tokens.WHITE,
    letter_spacing=2.2,
)
FEATURE_BODY = TextStyle(font_size_pt=8, font_weight=300, fill=tokens.TEXT_SOFT)
CARD_INDEX = TextStyle(
    font_size_pt=7,
    font_weight=800,
    fill=tokens.ACCENT_DARK,
    letter_spacing=2.4,
    font_family=tokens.MONO_FONT_FAMILY,
)
CARD_TAG = TextStyle(
    font_size_pt=7.2,
    font_weight=800,
    fill=tokens.MUTED,
    letter_spacing=2.2,
)
CARD_TITLE = TextStyle(
    font_size_pt=14,
    font_weight=700,
    fill=tokens.INK,
    letter_spacing=-0.4,
)
CARD_BODY = TextStyle(font_size_pt=8.5, font_weight=400, fill=tokens.INK_2)
METRIC_LABEL = TextStyle(
    font_size_pt=7.5,
    font_weight=800,
    fill=tokens.MUTED,
    letter_spacing=2.4,
)
METRIC_VALUE = TextStyle(
    font_size_pt=38,
    font_weight=800,
    fill=tokens.INK,
    letter_spacing=-1.6,
)
METRIC_DELTA = TextStyle(font_size_pt=8.5, font_weight=700, fill=tokens.ACCENT_DARK)
CHART_AXIS = TextStyle(
    font_size_pt=6.5,
    font_weight=600,
    fill=tokens.MUTED,
    letter_spacing=1.4,
)
CHART_ANNOTATION = TextStyle(
    font_size_pt=7.6,
    font_weight=700,
    fill=tokens.INK,
    letter_spacing=-0.05,
)
COUNTER_MONO_LIGHT = TextStyle(
    font_size_pt=8,
    font_weight=700,
    fill=tokens.WHITE,
    letter_spacing=1.8,
    font_family=tokens.MONO_FONT_FAMILY,
)

__all__ = [
    "CARD_BODY",
    "CARD_INDEX",
    "CARD_TAG",
    "CARD_TITLE",
    "CHART_ANNOTATION",
    "CHART_AXIS",
    "COUNTER_MONO_LIGHT",
    "DISPLAY_SERIF",
    "DISPLAY_XL",
    "DISPLAY_XL_EM",
    "EYEBROW",
    "EYEBROW_MUTED",
    "FEATURE_BODY",
    "FEATURE_INDEX",
    "FEATURE_TAG",
    "GIANT_NUMBER",
    "LEDE",
    "METRIC_DELTA",
    "METRIC_LABEL",
    "METRIC_VALUE",
    "PAGE_HEIGHT_MM",
    "PAGE_WIDTH_MM",
    "T",
]
