# folio

CLI for creating, building, previewing, validating, and reconciling SVG pages from a Python DSL.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

# bundled starter spec
folio validate config/folio.py
folio build config/folio.py
folio build config/folio.py --format idml   # writes out/folio.idml for InDesign handoff
folio reconcile out/cover.svg --spec config/folio.py
folio preview out/cover.svg --output out/cover.png

# scaffold from the built-in starter template
folio create my-doc \
  --var brand_name="ACME" \
  --var document_title="Ship layouts from Python." \
  --var document_kicker="STARTER TEMPLATE"

# self-contained project dir (preferred for real specs)
cd my-doc
folio validate        # resolves ./build.py by default
folio check           # validate + lint + typecheck (add --format or --fix as needed)
folio build
folio reconcile out/page1.svg --spec .
folio preview --spec .
```

## Template scaffolding

`folio create TARGET_DIR` scaffolds Folio's built-in starter template into a new target directory.
Use repeated `--var key=value` pairs to fill variables.

The starter produces a complete two-page project with:
- `build.py` render entrypoint
- `pages.py`, `layout.py`, `theme.py`
- `content.py` rendered from `content.py.j2` with sensible Jinja defaults
- `assets/.gitkeep` and `.gitignore`

Only template-marked files are rendered (`.j2`, `.jinja`, `.jinja2`); other files are copied verbatim.
Defaults live in the template itself, so `folio create my-doc` works without any `--var` flags.
Starter metadata lives in `src/folio/templates/starter/template.yaml`; keep that file descriptive and let `content.py.j2` remain the source of truth for default values.

## DSL reference (`folio docs`)

The full DSL surface is documented inside the installed package. Agents
and humans look symbols up through the CLI instead of grepping the
source:

```bash
folio docs search text           # find primitives related to text
folio docs show page             # signature, params, examples, source
folio docs show folio.dsl.rect   # fully-qualified lookup
folio docs list --kind=token     # every design token
folio docs list --kind=style     # every preset TextStyle
folio docs show page --format=json   # machine-readable view for agents
```

The index ships inside the installed wheel, so `folio docs` works from
any working directory regardless of where the Folio source lives.
Regenerate the committed index with `python -m folio.docs.generate`
after adding or modifying public DSL symbols.

## Agent skill

Agent-driven work on Folio projects is supported by a bundled skill
shipped inside the installed package. It installs into the
agent-neutral `.agents/skills/folio/` directory so it is not tied to any
one agent tool. Clients that read skills from a different path (for
example Claude Code's `.claude/skills/`) can symlink it.

`folio create` installs the skill into new projects by default at
`.agents/skills/folio/`; you can also install it on demand:

```bash
folio skill install                    # project scope (./.agents/skills/folio)
folio skill install --scope=user       # ~/.agents/skills/folio
folio skill install --force            # overwrite divergent installs

# if your agent tool reads from a client-specific path:
ln -s ~/.agents/skills/folio ~/.claude/skills/folio
```

The skill tells the agent to use `folio docs show` / `folio docs search`
for DSL lookups, and to follow the standard
`check → build → preview → reconcile` pipeline.

## Build outputs

`folio build` writes one SVG file per page by default. Use `--format idml` to write
both the normal page SVGs and `out/folio.idml`: a minimal IDML package with native,
editable layout objects for common Folio primitives such as rectangles, text frames,
lines, ovals, polygons, and polylines. This is an editable-structure MVP, not a full
SVG compatibility layer: filters, gradients, defs, arbitrary SVG path commands, and
image assets need additional mapping work. Uniform page sizes are the safest path for
this first IDML exporter; mixed-size documents should be opened and checked in the
target layout app.

## DSL entrypoint

A starter spec lives at `config/folio.py`.
For real projects, the preferred layout is a self-contained directory with `build.py` at the top level.
Implicit CLI lookup resolves `./build.py`; other spec files still work when passed explicitly.
Larger or private specs can live in any other Python module and still use the same public DSL from `folio.dsl`:

- `page()`
- `rect()`, `circle()`, `ellipse()`, `polygon()`, `polyline()`, `text()`, `multiline()`, `tspan()` / `span()`, `image()`, `group()`, `path()`, `line()`, `rule()`, `triangle()`, `qr()`
- `block()` for scoped IDs and local coordinates inside reusable components
- `PathBuilder` / `path_builder()` for mm-based path construction
- defs helpers like `linear_gradient()`, `linear_gradient_stops()`, `radial_gradient()`, `filter_()`, `drop_shadow()`, `gaussian_blur()`, `offset()`, `component_transfer()`, `func_a()`, `merge()`, `merge_node()`, `clip_path()`, `mask()`
- `render()`
- `tokens`
- `markup()` for trusted non-escaped text fragments

`page()`, `group()`, and defs helpers accept either the existing list/tuple style or slimmer variadic children.
`qr()` renders as ordinary SVG paths/rects, so it works without adding a renderer-specific element kind.
`text()` accepts either a plain string or a sequence of strings / `tspan()` fragments.
Use `markup()` instead of the old `raw=True` escape hatch when you need trusted literal markup.
`page()` also accepts `width_mm=` / `height_mm=` so you can use presets like `tokens.A5`, `tokens.DL`, `tokens.US_LETTER`, or `tokens.ROLLUP_850x2000`.
`tokens.extend(...)` lets a spec register additional named hex colors so validation treats them like first-class palette tokens.

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

For larger specs, prefer a self-contained project directory.
Because the loader inserts the spec directory on `sys.path`, `build.py` can import sibling modules directly.
Passing either the file path or the project directory works: `folio build my-doc/build.py` and `folio build my-doc/` resolve the same spec.

Recommended structure:

- `my-doc/build.py` — main spec entrypoint
- `my-doc/content.py` — content constants and copy blocks
- `my-doc/layout.py` — reusable helpers, components, defs, and layout utilities
- `my-doc/pages.py` — page-level assembly helpers that return `page(...)` nodes when a spec grows large
- `my-doc/assets/` — source images referenced by the spec
- `my-doc/.cache/` — build/reconcile/preview cache written beside the spec
- `my-doc/out/` — rendered SVG or PNG output (default when building that spec, even if the CLI is invoked elsewhere)

Layout helpers are available both as classes and convenience builders:

- `cols(n, inside=(left, right), gap=...)`
- `grid(cols, rows, inside=(x, y, width, height), col_gap=..., row_gap=...)`
- `flow_cols(n=3, inside=(x, y, width), gap=..., arrow_w=...)`

## Charts

`chart()` turns a matplotlib figure into a folio `Element` (kind `IMAGE`) that participates in the normal layout, reconcile, and SVG-embedding pipeline.
It is an optional feature — install with `pip install 'folio[charts]'` (or add matplotlib directly).

It accepts any library that writes into a matplotlib `Axes` (seaborn, pandas, matplotlib itself) or hands back a matplotlib `Figure`. Libraries that produce their own PNGs directly (Plotly static export, Altair) should keep using `image()`.

Three shapes, one code path:

```python
from folio.dsl import chart

# 1. Decorator — function takes an Axes. Most concise.
@chart("revenue", x_mm=20, y_mm=120, width_mm=80, height_mm=40)
def revenue(ax):
    ax.plot(months, values)
# `revenue` is now an Element

# 2. Context manager — when you want the Figure object alongside the Axes.
handle = chart("trends", x_mm=20, y_mm=120, width_mm=80, height_mm=40)
with handle as ax:
    ax.plot(...)
page(handle.element, ...)

# 3. Pre-built Figure — for libraries that hand back a Figure.
import seaborn as sns
fig = sns.lineplot(data=df).figure
element = chart("revenue", x_mm=20, y_mm=120, width_mm=80, height_mm=40).from_figure(fig)
```

Rendered PNGs are content-addressed by SHA-256 of the PNG bytes, so builds that produce identical figures reuse the cache. The cache lives at `<spec>/.folio-cache/charts/` by default; override with `FOLIO_CHART_CACHE_DIR` or the `cache_dir=` kwarg.

`dpi=300` is the default (print-ready); drop to 150 for drafts. `transparent=True` is the default so page tokens show through chart backgrounds.

## Notes

- Images are embedded as base64 data URIs.
- Cache lives beside the spec at `.cache/folio/<spec-cache-key>/` so multiple specs in one directory do not collide.
- `folio preview <svg>` rasterizes an arbitrary SVG to PNG; without an SVG argument it still previews cached last-build pages for a spec.
- `folio preview` prefers Playwright, then falls back to CairoSVG, `rsvg-convert`, or Inkscape when available.
