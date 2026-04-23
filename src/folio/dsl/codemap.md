# src/folio/dsl/

## Responsibility

The **Domain-Specific Language (DSL) layer** for folio. Provides a declarative Python API that translates high-level page layout descriptions into immutable intermediate data structures (`Document`, `Page`, `Element`, `DefNode`), which are then rendered into SVG output. The DSL is the primary authoring surface for users writing `build.py` specs.

## Design

### Architecture: Builder + Immutable Intermediate Model

The module follows a **two-phase design**:

1. **Builder phase** — Python functions in `builtins.py` construct frozen dataclass instances from `model.py` (`Element`, `Page`, `Document`, `DefNode`, `TextSpan`, etc.).
2. **Renderer phase** — `renderer.py` consumes those immutable structures and serializes them to SVG string output.

### Module Map

| File | Role |
|------|------|
| `model.py` | Immutable dataclass definitions for all intermediate types |
| `builtins.py` | Public DSL builder functions (`rect`, `text`, `group`, `page`, `render`, etc.) + `Block` scope helper + `PathBuilder` / `TransformBuilder` |
| `charts.py` | Matplotlib-backed chart primitive (`chart()` decorator/ctx/Figure API) |
| `styles.py` | `TextStyle` dataclass with attribute normalization + style composition |
| `tokens.py` | Design token re-exports (colors, sizes) + named style presets (`STYLES`) + `extend()` for runtime token extension |
| `loader.py` | DSL module loading pipeline (`load_dsl_module()`) — import, execute, extract `document`/`build()`/`pages` |
| `renderer.py` | Validation + SVG serialization — walks the intermediate model and emits SVG strings |
| `render.py` | Compatibility shim re-exporting `renderer.py` internals |
| `schema.py` | `DocumentFactory` protocol + `PageSequence` type alias |

### Element Model (model.py)

```
Document
  └── pages: tuple[Page, ...]
        ├── page_id, filename, page_number, width_mm, height_mm
        ├── elements: tuple[Element, ...]
        │     ├── kind: ElementKind (RECT, CIRCLE, ELLIPSE, TEXT, IMAGE, GROUP, PATH, POLYGON, POLYLINE, LINE)
        │     ├── element_id, x_mm, y_mm, content, attrs, children
        │     └── TextSpan: element_id, content, attrs (supports nested spans)
        └── defs: tuple[DefNode, ...]  # SVG <defs> entries (gradients, filters, clipPaths...)
              └── DefNode: tag, element_id, attrs, children, content
```

### Pattern: Builder Functions via Auto-ID

`builtins.py` exposes ~40 builder functions. Unnamed elements get auto-generated IDs via `_element_id(kind, element_id)` backed by a `defaultdict[str, int]` counter. IDs are reset per module load via `reset_auto_ids()`.

### Pattern: Block Scope (Layout Composition)

`Block` is a **composite/fluent builder** that carries an `x_mm`/`y_mm` offset. All element builders on `Block` (`rect()`, `text()`, etc.) auto-offset coordinates. Supports `.scope(suffix)` for nested sub-blocks. Enables relative layout composition without coordinate bookkeeping.

### Pattern: PathBuilder / TransformBuilder (Fluent Builder)

Both are mutable dataclass builders that accumulate SVG commands (`M`, `L`, `C`, `Q`, `A`, `Z` for paths; `translate`, `rotate`, `scale`, `skewX`, `skewY`, `matrix` for transforms) and produce a `build()` string.

### Pattern: TextStyle (Fluent Dataclass)

`TextStyle` is a frozen `slots=True` dataclass. Methods on it (`__call__`, `span()`, `multiline()`, `wrapped_text()`, `measure_text()`, `measure_wrapped_text()`) act as factory methods that call the corresponding `builtins.py` functions with the style pre-applied. Supports both `.call()` style and `style=style` kwarg usage.

### Pattern: ChartHandle (Decorator + Context Manager + Direct Figure)

`charts.py` exposes three usage patterns sharing one code path:
- `@chart("id", ...)` decorator
- `with chart("id", ...) as ax:` context manager
- `chart("id", ...).from_figure(fig)` for pre-built Figures

Rendered PNGs are content-addressed (SHA-256 digest) and cached under `<spec_dir>/.folio-cache/charts/`.

### Pattern: Text Wrap Algorithm (Greedy Line Breaker)

`builtins.py` `_wrap_layout()` implements a greedy word-wrapping algorithm:
1. Flattens content to runs → tokenizes to words/spaces/newlines
2. Accumulates tokens into lines respecting `width_mm`
3. Truncates final line with ellipsis if `max_lines` exceeded or content overflows
4. Returns `_WrappedLayout` with line contents + `TextMetrics`

Uses a `pt * PT_TO_MM * 0.53` ratio for glyph-width estimation. Markup content is treated as unsplittable.

### Pattern: SVG Defs Composition

DefNodes (`linear_gradient`, `drop_shadow`, `grain`, `clip_path`, etc.) are composable SVG `<defs>` primitives. `drop_shadow()` and `grain()` build full filter graphs via nested DefNode composition. `linear_gradient_stops()` creates gradient defs from `(offset, color, opacity?)` tuples.

## Data & Control Flow

### DSL Spec → SVG Output Pipeline

```
build.py (user code)
  └── load_dsl_module(path)           [loader.py]
        ├── importlib.util.spec_from_file_location
        ├── sys.modules[module_name] = module
        ├── dsl_builtins.reset_auto_ids()
        ├── dsl_charts.set_spec_base_dir(spec_dir)
        └── spec.loader.exec_module(module)
              └── module defines: document / build() / pages
                  └── document_from_module()        [renderer.py]
                        └── _coerce_document() → Document
                              └── validate_document()           [renderer.py]
                                    ├── _validate_document()      (id uniqueness, page constraints)
                                    └── _warn_on_non_token_hex_colors()
                              └── render_document()              [renderer.py]
                                    └── _render_page() for each page
                                          ├── _render_element()   (dispatches on ElementKind)
                                          ├── _defs_block()
                                          └── _normalize_svg_attrs()
                                          └── svg_open() → RenderedPage
                              └── BuildResult(pages, config_hash)
```

### DSL Builder Call Chain (builtins.py)

```
User: rect("id", 10, 20, 50, 30, fill="#000")
  └── _element_id("rect", "id") → "id" (or auto-generated)
  └── Element(kind=RECT, element_id="id", x_mm=10, y_mm=20, attrs={width_mm:50, height_mm:30, fill:"#000"})
```

```
User: text("id", 10, 20, "Hello", style=hero)
  └── tspan() → TextSpan(content="Hello", attrs={size_pt:38, weight:800, ...})
  └── Element(kind=TEXT, element_id="id", x_mm=10, y_mm=20, content=TextSpan/str/Markup)
```

```
User: wrapped_text("id", 10, 20, "Hello", width_mm=50)
  └── _wrap_layout() → _WrappedLayout(lines, metrics)
  └── multiline() → n × tspan() elements
```

```
User: qr("id", 10, 20, "https://...", size_mm=30)
  └── QrCode.encode_text()           [vendor.qrcodegen]
  └── _qr_path_data() → SVG path string
  └── group() → Element(GROUP) with background rect + path child
```

```
User: chart("id", x_mm=10, y_mm=20, width_mm=80, height_mm=40)
  └── @decorated: with self as ax: render(ax) → _rasterize()
        └── _figure_to_png_bytes() → SHA-256 digest
        └── image() → Element(IMAGE) with Asset(reference=<cached_png_path>)
```

### Token System

```
folio.dsl.tokens  (re-exports from folio.render.tokens)
  ├── Colors: INK, ACCENT, MUTED, WHITE, SOFT, LINE, DL, A4, A5, US_LETTER, ROLLUP_850x2000
  └── Sizes: A4_WIDTH_MM, A4_HEIGHT_MM, MM_TO_PT, PT_TO_MM
  └── extend(**colors) → adds runtime tokens to module globals + render_tokens
  └── STYLES namespace: named TextStyle presets (hero, kicker, stat_value, body, etc.)
```

## Integration

### Consumed By
- **CLI** (`src/folio/cli.py`) — calls `loader.load_dsl_module()` + `renderer.build_pages()` / `renderer.write_pages()`
- **Reconcile** (`src/folio/reconcile/`) — consumes `Element` trees to compute layout positions
- **Preview** (`src/folio/preview.py`) — renders pages for live preview

### Depends On
- `folio.render.tokens` — design tokens (colors, sizes)
- `folio.render.primitives` — low-level SVG primitive emitters (`rect_mm`, `circle_mm`, `text_mm`, etc.)
- `folio.vendor.qrcodegen` — QR code generation (`QrCode`)
- `matplotlib` (optional) — chart rasterization (lazy-imported)
- `jinja2` (indirect) — templating support
