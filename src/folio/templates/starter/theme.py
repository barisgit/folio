from __future__ import annotations

from folio.dsl import TextStyle, tokens

tokens.extend(
    ink_black="#04060d",
    deep_navy="#070c1d",
    glass_navy="#18284a",
    mid_navy="#132243",
    amber="#d9a64b",
    amber_deep="#b8862a",
    burgundy="#6b1c2a",
    coral="#ff5a3c",
    mist="#eef2f7",
    chalk="#f6f1e7",
    paper="#fbf7ee",
    carbon="#111823",
)

PAGE_SIZE_MM = 240.0
MARGIN_X_MM = 18.0
TOTAL_PAGES = 3

T = tokens.STYLES

DISPLAY_XL = TextStyle(
    font_size_pt=58,
    font_weight=800,
    fill=tokens.WHITE,
    letter_spacing=-2.2,
)
DISPLAY_XL_EM = TextStyle(
    font_size_pt=58,
    font_weight=800,
    fill=tokens.ACCENT,
    letter_spacing=-2.2,
    font_style="italic",
)
DISPLAY_SERIF = TextStyle(
    font_size_pt=58,
    font_weight=300,
    fill=tokens.WHITE,
    letter_spacing=-2.2,
    font_family="'Playfair Display', 'Iowan Old Style', Georgia, serif",
    font_style="italic",
)
DISPLAY_L = TextStyle(
    font_size_pt=40,
    font_weight=300,
    fill=tokens.INK,
    letter_spacing=-1.2,
)
DISPLAY_L_SERIF = TextStyle(
    font_size_pt=40,
    font_weight=700,
    fill=tokens.ACCENT_DARK,
    letter_spacing=-1.2,
    font_family="'Playfair Display', 'Iowan Old Style', Georgia, serif",
    font_style="italic",
)
GIANT_NUMBER = TextStyle(
    font_size_pt=340,
    font_weight=900,
    fill=tokens.ACCENT,
    fill_opacity=0.07,
    letter_spacing=-16.0,
)
EYEBROW = TextStyle(
    font_size_pt=7.6,
    font_weight=800,
    fill=tokens.ACCENT,
    letter_spacing=4.0,
)
EYEBROW_DARK = TextStyle(
    font_size_pt=7.2,
    font_weight=800,
    fill=tokens.ACCENT_DARK,
    letter_spacing=4.0,
)
EYEBROW_MUTED = TextStyle(
    font_size_pt=7.0,
    font_weight=700,
    fill=tokens.MUTED_LIGHT,
    letter_spacing=3.2,
)
LEDE_LIGHT = TextStyle(
    font_size_pt=10.5,
    font_weight=300,
    fill=tokens.WHITE,
    fill_opacity=0.82,
    letter_spacing=-0.05,
)
LEDE_LIGHT_EM = TextStyle(
    font_size_pt=10.5,
    font_weight=600,
    fill=tokens.WHITE,
    letter_spacing=-0.05,
    font_family="'Playfair Display', 'Iowan Old Style', Georgia, serif",
    font_style="italic",
)
LEDE_DARK = TextStyle(
    font_size_pt=11,
    font_weight=300,
    fill=tokens.INK_2,
    letter_spacing=-0.05,
)
LEDE_DARK_EM = TextStyle(
    font_size_pt=11,
    font_weight=700,
    fill=tokens.ACCENT_DARK,
    letter_spacing=-0.05,
    font_family="'Playfair Display', 'Iowan Old Style', Georgia, serif",
    font_style="italic",
)
FEATURE_INDEX = TextStyle(
    font_size_pt=7.2,
    font_weight=800,
    fill=tokens.ACCENT,
    letter_spacing=2.4,
    font_family=tokens.MONO_FONT_FAMILY,
)
FEATURE_TAG = TextStyle(
    font_size_pt=7.8,
    font_weight=800,
    fill=tokens.WHITE,
    letter_spacing=2.2,
)
FEATURE_BODY = TextStyle(font_size_pt=8.2, font_weight=300, fill=tokens.TEXT_SOFT)
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
CARD_BODY = TextStyle(font_size_pt=8.6, font_weight=400, fill=tokens.INK_2)
METRIC_LABEL = TextStyle(
    font_size_pt=7.5,
    font_weight=800,
    fill=tokens.MUTED,
    letter_spacing=2.4,
)
METRIC_VALUE = TextStyle(
    font_size_pt=44,
    font_weight=800,
    fill=tokens.INK,
    letter_spacing=-1.8,
)
METRIC_DELTA = TextStyle(font_size_pt=8.6, font_weight=700, fill=tokens.ACCENT_DARK)
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
COUNTER_MONO_DARK = TextStyle(
    font_size_pt=8,
    font_weight=700,
    fill=tokens.MUTED,
    letter_spacing=1.8,
    font_family=tokens.MONO_FONT_FAMILY,
)
BRAND_NAME_LIGHT = TextStyle(
    font_size_pt=11.5,
    font_weight=800,
    fill=tokens.WHITE,
    letter_spacing=1.8,
)
BRAND_NAME_DARK = TextStyle(
    font_size_pt=11.5,
    font_weight=800,
    fill=tokens.INK,
    letter_spacing=1.8,
)
BRAND_TAGLINE_LIGHT = TextStyle(
    font_size_pt=6.8,
    font_weight=700,
    fill=tokens.ACCENT,
    letter_spacing=2.8,
)
BRAND_TAGLINE_DARK = TextStyle(
    font_size_pt=6.8,
    font_weight=700,
    fill=tokens.ACCENT_DARK,
    letter_spacing=2.8,
)
CAPTION_LIGHT = TextStyle(
    font_size_pt=7.0,
    font_weight=400,
    fill=tokens.WHITE,
    fill_opacity=0.78,
    letter_spacing=0.2,
)

__all__ = [
    "BRAND_NAME_DARK",
    "BRAND_NAME_LIGHT",
    "BRAND_TAGLINE_DARK",
    "BRAND_TAGLINE_LIGHT",
    "CAPTION_LIGHT",
    "CARD_BODY",
    "CARD_INDEX",
    "CARD_TAG",
    "CARD_TITLE",
    "CHART_ANNOTATION",
    "CHART_AXIS",
    "COUNTER_MONO_DARK",
    "COUNTER_MONO_LIGHT",
    "DISPLAY_L",
    "DISPLAY_L_SERIF",
    "DISPLAY_SERIF",
    "DISPLAY_XL",
    "DISPLAY_XL_EM",
    "EYEBROW",
    "EYEBROW_DARK",
    "EYEBROW_MUTED",
    "FEATURE_BODY",
    "FEATURE_INDEX",
    "FEATURE_TAG",
    "GIANT_NUMBER",
    "LEDE_DARK",
    "LEDE_DARK_EM",
    "LEDE_LIGHT",
    "LEDE_LIGHT_EM",
    "MARGIN_X_MM",
    "METRIC_DELTA",
    "METRIC_LABEL",
    "METRIC_VALUE",
    "PAGE_SIZE_MM",
    "T",
    "TOTAL_PAGES",
]
