# src/folio/commands/

## Responsibility
Command-layer CLI interface built on [Typer](https://typer.tiangolo.com/). Each subcommand maps to a discrete workflow: building specs into declared export targets, validating DSL source, rasterizing SVGs, reconciling edited SVGs against cached baselines, running lint/type checks, scaffolding new projects, and searching for assets.

## Design

### Architecture
- **Facade `__init__.py`** — Re-exports the public `typer.Typer` instance (`search_app`) and all command callables. Acts as the single import point for the CLI layer.
- **One file per command** — Follows the Typer convention of one module per subcommand, keeping each command's argument parsing and orchestration isolated.
- **`search/`** — Nested Typer app (`typer.Typer`) registered as a subcommand group. Two leaf commands: `stock_command` and `svg_command`. The `__init__.py` re-exports both the `app` instance and the underlying functions (`fetch_stock`, `search_svg_assets`) for programmatic reuse.

### Commands

| Module | CLI Entry | Purpose |
|--------|-----------|---------|
| `build.py` | `folio build` | Load DSL spec, build requested export targets, update cache |
| `validate.py` | `folio validate` | Load DSL module, build document, assert validity |
| `rasterize.py` | `folio rasterize` | Rasterize explicit or cached SVGs to PNG via `preview.py` backend |
| `reconcile.py` | `folio reconcile` | Parse edited SVG, diff against cached baseline, write JSON report |
| `check.py` | `folio check` | Run lint, typecheck, format checks via `folio.check` runner |
| `create.py` | `folio create` | Scaffold new project from Jinja2 starter template |
| `search.py` | `folio search` | (re-export of `search_app` Typer group) |
| `search/stock.py` | `folio search stock` | Stock image search via Openverse/Pexels/Pixabay |
| `search/svg.py` | `folio search svg` | SVG asset search via SVGL/Lordicon/Noun Project |

### Error Handling Pattern
Commands catch domain-specific exceptions (`DslError`, `RenderError`, `CacheError`, `ParseError`, `SvgSearchError`, `PreviewError`) and exit with a non-zero exit code. Typer's `typer.Exit` is used explicitly to control the exit code (1=general, 2=render/cache, 3=reconcile-changes). Rich `Console` is used for styled output.

### `reconcile.py` Flow
1. Resolve spec path → enumerate cached pages via `cached_pages()`
2. For each page: read baseline SVG → parse to `ParsedSvg` → diff with edited SVG → produce `DiffResult`
3. Build `report_payload` → write JSON report to `reconcile_report_path()` → print or JSON-serialize output
4. Exit code 3 if any page had changes.

### `create.py` Design
- Uses `importlib.resources` to locate the built-in starter template (`folio/templates/starter/`)
- Recursive directory copy with Jinja2 rendering of filenames and file contents (`.j2` suffix)
- Variables injected via `--var key=value` CLI option, with `project_slug` auto-derived from target directory name using PyPA-safe slugification
- Strict undefined: Jinja2 `StrictUndefined` raises on missing variables

### `search/` Sub-package
- **`search/stock.py`**: Thin Typer wrapper around `folio.search.providers` (`fetch_stock`, `fetch_stock_multi`). Supports multi-provider fan-out (openverse/pexels/pixabay) and `--json` output mode. Table rendering via `rich.table.Table`.
- **`search/svg.py`**: Thin Typer wrapper around `folio.search.svg` (`search_svg_assets`). Supports per-source filtering and `--json` output. Results rendered as a `rich.table.Table`.

## Flow

```
CLI invocation (folio <cmd>)
  → typer resolves subcommand
  → calls command function with Annotated[typer.Argument/Option] params
  → resolves spec_path via folio.dsl.loader.resolve_spec_path()
  → delegates to domain layer (dsl, render, cache, check, reconcile, rasterize/preview, search)
  → catches domain exceptions → prints styled error → exits with code
```

## Integration

- **Consumed by**: `folio.cli` (wires all commands via `app.add_typer()`)
- **Depends on**:
  - `folio.dsl.loader` — DSL module loading and spec path resolution
  - `folio.dsl.renderer` — `build_pages`, `validate_document`, `document_from_module`
  - `folio.cache` — `cache_build`, `cached_pages`, `last_build_svg`, `reconcile_report_path`
  - `folio.check.runner` — `run_check`, `CheckResult`
  - `folio.preview` — raster rendering backend used by `render_raster` / `render_preview_file`
  - `folio.reconcile.diff` — `diff_svgs`
  - `folio.reconcile.parse` — `parse_svg`, `ParsedSvg`, `ParseError`
  - `folio.reconcile.report` — `print_report`, `report_payload`, `write_report`
  - `folio.search.providers` — `fetch_stock`, `fetch_stock_multi`, `SearchResult`
  - `folio.search.svg` — `search_svg_assets`, `SvgSearchResponse`, `SvgSearchError`
  - `jinja2` — template rendering in `create.py`
  - `importlib.resources` — template resource access in `create.py`
  - `rich` — console output and tables
  - `typer` — CLI framework
