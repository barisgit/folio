"""Classification registry for the public DSL surface.

`DSL_KINDS` maps every name in `folio.dsl.__all__` to its `kind` category.
The generator uses this to classify symbols on the first of three discovery
surfaces. Surfaces two (`folio.dsl.tokens`) and three
(`folio.dsl.tokens.STYLES`) are self-classifying — tokens entries are either
`token` (values) or `helper` (callables), and STYLES entries are always
`style`.
"""

from __future__ import annotations

from typing import TypedDict

DSL_KINDS: dict[str, str] = {
    # Types and classes
    "Asset": "helper",
    "Block": "builder",
    "ChartHandle": "helper",
    "DefNode": "defs",
    "Document": "primitive",
    "DocumentCollection": "primitive",
    "Element": "primitive",
    "ElementKind": "primitive",
    "ExportFormat": "helper",
    "ExportPreset": "helper",
    "ExportScope": "helper",
    "Markup": "primitive",
    "Page": "primitive",
    "PathBuilder": "builder",
    "TextLayoutWarning": "helper",
    "TextMetrics": "helper",
    "TextSpan": "primitive",
    "TextStyle": "style",
    "TransformBuilder": "builder",
    # Shape primitives (produce Element)
    "circle": "primitive",
    "ellipse": "primitive",
    "group": "primitive",
    "image": "primitive",
    "line": "primitive",
    "markup": "primitive",
    "multiline": "primitive",
    "page": "primitive",
    "path": "primitive",
    "polygon": "primitive",
    "polyline": "primitive",
    "qr": "primitive",
    "rect": "primitive",
    "rule": "primitive",
    "span": "primitive",
    "text": "primitive",
    "triangle": "primitive",
    "tspan": "primitive",
    "wrapped_text": "primitive",
    # Defs (SVG <defs> children)
    "clip_path": "defs",
    "component_transfer": "defs",
    "drop_shadow": "defs",
    "filter_": "defs",
    "func_a": "defs",
    "gaussian_blur": "defs",
    "grain": "defs",
    "linear_gradient": "defs",
    "linear_gradient_stops": "defs",
    "mask": "defs",
    "merge": "defs",
    "merge_node": "defs",
    "offset": "defs",
    "radial_gradient": "defs",
    "stop": "defs",
    "svg_node": "defs",
    # Builders (fluent constructors)
    "block": "builder",
    "path_builder": "builder",
    "transform_builder": "builder",
    # Helpers (measurement, rasterization, top-level renderer)
    "chart": "helper",
    "collection": "helper",
    "document": "helper",
    "idml": "helper",
    "measure_text": "helper",
    "measure_wrapped_text": "helper",
    "pdf": "helper",
    "png": "helper",
    "render": "helper",
    "svg": "helper",
    # Layout helpers
    "cols": "helper",
    "flow_cols": "helper",
    "grid": "helper",
    # Module re-export
    "tokens": "helper",
}


DEFAULT_EXAMPLE_SETUP: str = (
    "from folio.dsl import *  # noqa: F401,F403\nfrom folio.dsl import tokens  # noqa: F401\n"
)


class TokenEntry(TypedDict, total=False):
    summary: str
    description: str
    examples: list[tuple[str, str | None]]
    tags: tuple[str, ...]


TOKEN_DOCS: dict[str, TokenEntry] = {
    "A4": {
        "summary": "A4 page dimensions as (width_mm, height_mm).",
        "examples": [("tokens.A4", "Tuple of (width_mm, height_mm).")],
        "tags": ("page", "size"),
    },
    "A4_HEIGHT_MM": {
        "summary": "A4 page height in millimeters.",
        "examples": [("tokens.A4_HEIGHT_MM", None)],
        "tags": ("page", "size"),
    },
    "A4_HEIGHT_PT": {
        "summary": "A4 page height in PDF points.",
        "examples": [("tokens.A4_HEIGHT_PT", None)],
        "tags": ("page", "size"),
    },
    "A4_WIDTH_MM": {
        "summary": "A4 page width in millimeters.",
        "examples": [("tokens.A4_WIDTH_MM", None)],
        "tags": ("page", "size"),
    },
    "A4_WIDTH_PT": {
        "summary": "A4 page width in PDF points.",
        "examples": [("tokens.A4_WIDTH_PT", None)],
        "tags": ("page", "size"),
    },
    "A5": {
        "summary": "A5 page dimensions as (width_mm, height_mm).",
        "examples": [("tokens.A5", None)],
        "tags": ("page", "size"),
    },
    "ACCENT": {
        "summary": "Primary accent color token.",
        "examples": [("rect(None, 0, 0, 10, 10, fill=tokens.ACCENT)", None)],
        "tags": ("color", "accent"),
    },
    "ACCENT_DARK": {
        "summary": "Darker accent color token.",
        "examples": [("rect(None, 0, 0, 10, 10, fill=tokens.ACCENT_DARK)", None)],
        "tags": ("color", "accent"),
    },
    "BLUE_GLOW": {
        "summary": "Blue glow accent color token.",
        "examples": [("rect(None, 0, 0, 10, 10, fill=tokens.BLUE_GLOW)", None)],
        "tags": ("color", "accent"),
    },
    "DEFAULT_FONT_FAMILY": {
        "summary": "Default sans-serif font stack for body text.",
        "examples": [("tokens.DEFAULT_FONT_FAMILY", None)],
        "tags": ("typography",),
    },
    "DL": {
        "summary": "DL envelope dimensions as (width_mm, height_mm).",
        "examples": [("tokens.DL", None)],
        "tags": ("page", "size"),
    },
    "INK": {
        "summary": "Primary ink color token (darkest text color).",
        "examples": [("text(None, 10, 10, 'Hi', fill=tokens.INK)", None)],
        "tags": ("color", "ink"),
    },
    "INK_2": {
        "summary": "Secondary ink color token.",
        "examples": [("text(None, 10, 10, 'Body', fill=tokens.INK_2)", None)],
        "tags": ("color", "ink"),
    },
    "INK_3": {
        "summary": "Tertiary ink color token.",
        "examples": [("rect(None, 0, 0, 10, 10, fill=tokens.INK_3)", None)],
        "tags": ("color", "ink"),
    },
    "INK_4": {
        "summary": "Quaternary ink color token.",
        "examples": [("rect(None, 0, 0, 10, 10, fill=tokens.INK_4)", None)],
        "tags": ("color", "ink"),
    },
    "LINE": {
        "summary": "Neutral rule/divider line color token.",
        "examples": [("rule(None, 0, 0, 40, fill=tokens.LINE)", None)],
        "tags": ("color", "line"),
    },
    "MM_TO_PT": {
        "summary": "Unit conversion factor from millimeters to PDF points.",
        "examples": [("10 * tokens.MM_TO_PT", "Convert 10 mm to points.")],
        "tags": ("units",),
    },
    "MONO_FONT_FAMILY": {
        "summary": "Monospace font stack for tabular/code text.",
        "examples": [("tokens.MONO_FONT_FAMILY", None)],
        "tags": ("typography",),
    },
    "MUTED": {
        "summary": "Muted neutral text color token.",
        "examples": [("text(None, 10, 10, 'Meta', fill=tokens.MUTED)", None)],
        "tags": ("color", "muted"),
    },
    "MUTED_LIGHT": {
        "summary": "Lighter muted neutral color token.",
        "examples": [("text(None, 10, 10, 'Meta', fill=tokens.MUTED_LIGHT)", None)],
        "tags": ("color", "muted"),
    },
    "MUTED_SOFT": {
        "summary": "Soft muted neutral color token.",
        "examples": [("text(None, 10, 10, 'Meta', fill=tokens.MUTED_SOFT)", None)],
        "tags": ("color", "muted"),
    },
    "PT_TO_MM": {
        "summary": "Unit conversion factor from PDF points to millimeters.",
        "examples": [("12 * tokens.PT_TO_MM", "Convert 12 pt to mm.")],
        "tags": ("units",),
    },
    "ROLLUP_850x2000": {
        "summary": "Rollup banner dimensions 850x2000 mm.",
        "examples": [("tokens.ROLLUP_850x2000", None)],
        "tags": ("page", "size"),
    },
    "SOFT": {
        "summary": "Soft panel background color token.",
        "examples": [("rect(None, 0, 0, 10, 10, fill=tokens.SOFT)", None)],
        "tags": ("color", "surface"),
    },
    "TEXT_SOFT": {
        "summary": "Soft text color token for body copy on dark surfaces.",
        "examples": [("text(None, 10, 10, 'Body', fill=tokens.TEXT_SOFT)", None)],
        "tags": ("color", "text"),
    },
    "US_LETTER": {
        "summary": "US Letter page dimensions as (width_mm, height_mm).",
        "examples": [("tokens.US_LETTER", None)],
        "tags": ("page", "size"),
    },
    "WHITE": {
        "summary": "Pure white color token.",
        "examples": [("rect(None, 0, 0, 10, 10, fill=tokens.WHITE)", None)],
        "tags": ("color",),
    },
}
"""Per-token documentation metadata for scalars under `folio.dsl.tokens`.

Each entry is `{"summary": str, "description": str, "tags": tuple[str, ...],
"examples": list[tuple[str, str | None]]}`. Callable tokens (e.g.
`extend`) pull their docs from the function's docstring and are not listed
here.
"""


def _style_entry(name: str, summary: str) -> TokenEntry:
    return {
        "summary": summary,
        "examples": [
            (f"tokens.STYLES.{name}(None, 0, 0, 'Sample')", "Render as a text element."),
        ],
        "tags": ("text", "style"),
    }


STYLE_DOCS: dict[str, TokenEntry] = {
    "hero": _style_entry("hero", "Hero-scale display title preset (38pt, 800, white)."),
    "hero_subtitle": _style_entry(
        "hero_subtitle", "Subtitle paired with hero titles (11.5pt, 300, white)."
    ),
    "kicker": _style_entry(
        "kicker", "Kicker/eyebrow label preset (8pt, 700, accent, wide tracking)."
    ),
    "stat_value": _style_entry(
        "stat_value", "Emphatic numeric stat value preset (13pt, 700, white)."
    ),
    "stat_detail": _style_entry(
        "stat_detail", "Small caption under stat values (6.8pt, 400, muted soft)."
    ),
    "feature_title": _style_entry(
        "feature_title", "Feature card title preset (9.5pt, 600, white)."
    ),
    "feature_body": _style_entry(
        "feature_body", "Feature card body preset (8.5pt, 400, soft text)."
    ),
    "flow_label": _style_entry("flow_label", "Flow step label preset (8pt, 700, dark accent)."),
    "flow_body": _style_entry("flow_body", "Flow step body preset (8.5pt, 400, secondary ink)."),
    "capture_title": _style_entry(
        "capture_title", "Capture block title preset (7pt, 700, muted, tracked)."
    ),
    "capture_value": _style_entry("capture_value", "Capture block value preset (9pt, 600, ink)."),
    "capture_body": _style_entry(
        "capture_body", "Capture block body preset (7.5pt, 400, secondary ink)."
    ),
    "audience_title": _style_entry(
        "audience_title", "Audience section title preset (9.5pt, 700, accent)."
    ),
    "audience_body": _style_entry(
        "audience_body", "Audience section body preset (8.5pt, 400, soft text)."
    ),
    "brand_name": _style_entry("brand_name", "Brand wordmark preset (22pt, 800, white)."),
    "brand_tagline": _style_entry(
        "brand_tagline", "Brand tagline preset (8.5pt, 700, accent, tracked)."
    ),
    "meta": _style_entry("meta", "Page meta/footer preset (8pt, 400, light muted, tracked)."),
    "counter_mono": _style_entry(
        "counter_mono", "Monospace counter preset (8pt, 400, muted, mono family)."
    ),
    "bottom_claim": _style_entry("bottom_claim", "Bottom closing claim preset (11pt, 500, white)."),
    "body": _style_entry("body", "Default body copy preset (8.5pt, 400, secondary ink)."),
    "body_large": _style_entry(
        "body_large", "Large body copy preset (10.5pt, 300, secondary ink)."
    ),
    "caption": _style_entry("caption", "Caption preset (alias of stat_detail)."),
    "page_title": _style_entry("page_title", "Page-level title preset (14pt, 800, ink)."),
    "section_label": _style_entry(
        "section_label", "Section label preset (7.5pt, 700, dark accent, tracked)."
    ),
    "title": _style_entry("title", "Generic title preset (9.5pt, 600)."),
    "title_large": _style_entry("title_large", "Large title preset (alias of page_title)."),
    # Uppercase aliases
    "BODY": _style_entry("BODY", "Uppercase alias for the body preset."),
    "BODY_LG": _style_entry("BODY_LG", "Uppercase alias for the body_large preset."),
    "CAPTION": _style_entry("CAPTION", "Uppercase alias for the caption preset."),
    "DISPLAY": _style_entry("DISPLAY", "Uppercase alias for the hero display preset."),
    "KICKER": _style_entry("KICKER", "Uppercase alias for the kicker preset."),
    "LABEL": _style_entry("LABEL", "Uppercase alias for the section_label preset."),
    "LEAD": _style_entry("LEAD", "Uppercase alias for the hero_subtitle preset."),
    "META": _style_entry("META", "Uppercase alias for the meta preset."),
    "META_MONO": _style_entry("META_MONO", "Uppercase alias for the counter_mono preset."),
    "STAT_VALUE": _style_entry("STAT_VALUE", "Uppercase alias for the stat_value preset."),
    "TITLE": _style_entry("TITLE", "Uppercase alias for the title preset."),
    "TITLE_LG": _style_entry("TITLE_LG", "Uppercase alias for the title_large preset."),
}
"""Per-style documentation metadata for every `TextStyle` under
`folio.dsl.tokens.STYLES`."""
