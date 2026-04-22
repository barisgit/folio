# folio

CLI for building, previewing, validating, and reconciling SVG pages from a Python DSL.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
folio validate config/folio.py
folio build config/folio.py
folio reconcile out/cover.svg --spec config/folio.py
folio preview out/cover.svg --output out/cover.png
```

## DSL entrypoint

A starter spec lives at `config/folio.py`.
Larger or private specs can live in any other Python module and still use the same public DSL from `folio.dsl`:

- `page()`
- `rect()`, `circle()`, `text()`, `multiline()`, `tspan()` / `span()`, `image()`, `group()`, `path()`, `line()`, `rule()`, `triangle()`
- `block()` for scoped IDs and local coordinates inside reusable components
- defs helpers like `linear_gradient()`, `radial_gradient()`, `filter_()`, `gaussian_blur()`, `offset()`, `component_transfer()`, `func_a()`, `merge()`, `merge_node()`, `clip_path()`
- `render()`
- `tokens`
- `markup()` for trusted non-escaped text fragments

`page()`, `group()`, and defs helpers accept either the existing list/tuple style or slimmer variadic children.
`text()` accepts either a plain string or a sequence of strings / `tspan()` fragments.
Use `markup()` instead of the old `raw=True` escape hatch when you need trusted literal markup.

Text presets live under `tokens.STYLES.*`, and they are callable: `tokens.STYLES.hero(...)`, `tokens.STYLES.kicker.span(...)`, and `tokens.STYLES.body.multiline(...)` all build the corresponding nodes while still allowing keyword overrides.

```python
from folio.dsl import block, page, rect, render, tokens

T = tokens.STYLES
card = block("card", at=(20, 40))

document = render(
    page(
        rect("cover_bg", 0, 0, tokens.A4_WIDTH_MM, tokens.A4_HEIGHT_MM, fill=tokens.INK),
        T.hero("headline", 16, 24, "Hello DSL", size_pt=22),
        card.layer(
            "Card",
            card.rect("panel", 0, 0, 64, 24, fill=tokens.SOFT, rx_mm=2.0, ry_mm=2.0),
            card.text("body", 4, 8, "Shorter, still explicit.", style=T.body),
            card.rule("sep", 0, 18, 64, fill=tokens.LINE, opacity=0.4),
        ),
        page_id="cover",
        filename="cover.svg",
        page_number=1,
    )
)
```

## Layout

- `src/folio/cli.py` — Typer entrypoint
- `src/folio/commands/` — CLI command modules
- `src/folio/dsl/` — canonical document model, DSL loader, and SVG renderer
- `src/folio/render/` — generic SVG primitives and design tokens
- `src/folio/reconcile/` — SVG parse/diff/report
- `src/folio/layout/` — reusable layout helpers (`Columns`, `Grid`, `cols()`, `grid()`, `flow_cols()`)
- `config/folio.py` — starter Python DSL spec

## Recommended spec split pattern

For larger specs, keep the public entrypoint at a stable path like `config/project.py`, and move most implementation into sibling importable modules under `config/`.
Because the loader inserts the spec directory on `sys.path`, a package such as `config/project_example/` can be imported directly from the entrypoint.

Recommended structure:

- `config/project.py` — thin wrapper / stable public entrypoint, plus any compatibility re-exports callers rely on
- `config/project_example/content.py` — content constants and copy blocks
- `config/project_example/layout.py` — reusable helpers, components, defs, and layout utilities
- `config/project_example/pages.py` — page-level assembly helpers that return `page(...)` nodes when a spec grows large
- `config/project_example/build.py` — thin `build()` orchestration

Layout helpers are available both as classes and convenience builders:

- `cols(n, inside=(left, right), gap=...)`
- `grid(cols, rows, inside=(x, y, width, height), col_gap=..., row_gap=...)`
- `flow_cols(n=3, inside=(x, y, width), gap=..., arrow_w=...)`

## Notes

- Images are embedded as base64 data URIs.
- Cache lives beside the spec at `.cache/folio/<spec-cache-key>/` so multiple specs in one directory do not collide.
- `folio preview <svg>` rasterizes an arbitrary SVG to PNG; without an SVG argument it still previews cached last-build pages for a spec.
- `folio preview` requires Playwright and browser binaries.
