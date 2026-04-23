# src/folio/render/

## Responsibility
Provides a stateless SVG primitive layer that converts Python values into well-formed SVG XML strings. Acts as a pure rendering backend: it receives typed geometric/textual data and emits serialized SVG markup with no side effects (except for a module-level `_DATA_URI_CACHE`).

## Design

### Unit Conversion
- `tokens.MM_TO_PT = 72/25.4` and `tokens.PT_TO_MM = 25.4/72` are the canonical conversion factors.
- `m(value_mm)` rounds to 2 decimal places in pt units — all SVG coordinate attributes go through this.
- `pt_to_mm(value_pt)` is the inverse for point-based input.

### Attribute Builder (`_attrs`)
- Accepts any `Mapping[str, object]`. Skips `None` values. Joins `key="value"` pairs with a leading space.
- Used uniformly across all primitive functions — ensures consistent, idempotent attribute serialization.

### Data URI Inline Embedding
- `_data_uri(asset_path)` base64-encodes a file and embeds it as a `data:` URI.
- `_DATA_URI_CACHE` is a module-level `dict[Path, str]` — lazy, unbounded, process-lifetime cache keyed by `Path`. No eviction; suitable for CLI use-cases where the process lifetime is short.

### Primitive Functions
Every primitive follows the same contract: `(element_id, *geometry, **attrs) -> str`. Element IDs are nullable (`str | None`); `None` is passed through to `_attrs` and omitted via the `id` attribute check.

| Function | SVG Element | Notes |
|---|---|---|
| `rect_mm` | `<rect>` | fill required, arbitrary kwargs forwarded |
| `circle_mm` | `<circle>` | cx, cy, r in mm |
| `ellipse_mm` | `<ellipse>` | rx, ry in mm (not re-exported in `__init__`) |
| `path` | `<path>` | Takes pre-formatted `d` string |
| `polygon_mm` | `<polygon>` | `_points_attr` flattens `Sequence[tuple[float,float]]` |
| `polyline_mm` | `<polyline>` | same point format |
| `line_mm` | `<line>` | x1/y1/x2/y2 in mm |
| `image_mm` | `<image>` | Both `href` and `xlink:href` set; aspect ratio preserved |
| `text_mm` | `<text>` | Full font pipeline: size, weight, italic, family, letter-spacing, anchor |
| `tspan` | `<tspan>` | Stateless inline text span |
| `multiline_text_mm` | `<text>` with nested `<tspan>`s | Line step in mm; one tspan per line |
| `grid_lines_mm` | `<path>` | Horizontal/vertical grid as single combined path; opacity and stroke-width are kwargs, not hardcoded |
| `group` | `<g>` | Sets `id`, `inkscape:label`; content is a string (SVG snippet) |

### Token Module (`tokens.py`)
Pure constants: conversion factors, page size tuples, font family strings, and a fixed palette (WHITE, INK variants, MUTED, ACCENT, BLUE_GLOW). No logic — just named values.

## Flow

```
layout module (coordinates, styles)
    ↓ dict of primitives
render primitives (converts geometry to SVG strings)
    ↓
"".join(all_strings)  (no intermediate AST)
    ↓
svg_open()            (header + viewBox)
    ↓
full SVG document
```

## Integration
- Consumed by: `src/folio/layout/` — layout modules call primitive functions and concatenate results to build complete SVG documents.
- Depends on: `tokens.py` (constants only).
- Exported symbols: see `__all__` in `__init__.py`.
