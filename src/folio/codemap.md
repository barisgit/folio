# src/folio/

## Responsibility

The `folio` package is a **Python DSL SVG page builder and reconciliation CLI**. It provides:
1. A Python-based embedded DSL (`folio.dsl`) for declaratively authoring page layouts
2. A Typer-based CLI (`folio.cli`) exposing subcommands for build, preview, check, validate, reconcile, create, and search
3. A build artifact cache layer (`folio.cache`) with content-addressed SHA-256 manifests
4. A pluggable preview rasterizer (`folio.preview`) with graceful degradation across four backends

## Design

### CLI Architecture (Facade + Command Pattern)
- `cli.py` is the **Typer application root** — wires 7 subcommands via `app.command()` and `app.add_typer()` to command functions exported from `folio.commands.*`
- `__init__.py` re-exports all command callables for clean public API
- `__main__.py` enables `python -m folio` entry point, delegating to `cli.app`

### DSL Pipeline (Builder → Immutable Model → Renderer)
- `dsl.loader`: Resolves spec paths, imports Python DSL modules dynamically via `importlib`, and extracts page configuration
- `dsl.renderer`: Builds typed `BuildResult` objects from DSL modules, serializes to SVG strings, writes to disk

### Cache Layer (Write-Through + Manifest Pattern)
- `cache.py` uses **frozen dataclasses** (`CachePaths`, `CachedPage`, `CachedBuildFiles`) and content-addressed SHA-256 keys
- `_spec_cache_key()` derives a stable cache key from spec path + 10-char hash
- `cache_build()` writes all pages + a `manifest.json` atomically; `cached_pages()` reads and validates the manifest
- `CacheError` is the unified exception for all cache miss/corruption scenarios

### Preview Pipeline (Strategy + Fallback Chain)
- `preview.py` implements a **fallback chain** across four backends (Playwright → CairoSVG → rsvg-convert → Inkscape)
- `_default_viewport()` parses SVG `width`/`height` attributes, `viewBox`, or falls back to A4 at 96 DPI
- `_render_svg_preview()` iterates the renderer list, catching exceptions, and raises `PreviewError` listing all failures

### Command Modules (Thin Adapters)
Each command in `commands/` is a thin adapter that:
1. Resolves paths / arguments via `resolve_spec_path()`
2. Calls domain logic (cache, DSL loader, reconcile, preview)
3. Formats output via `rich.console.Console` and exits with semantic codes

### Config Module
- `config.py` is a stub reserved for project-specific config helpers

## Flow

### Build Pipeline
```
build_command(spec_path)
  → resolve_spec_path()         [dsl.loader]
  → load_dsl_module()            [dsl.loader]
  → build_pages()                [dsl.renderer]
  → write_pages()                [dsl.renderer]
  → cache_build()                [cache.py]  (unless --no-cache)
```

### Rasterize Pipeline
```
rasterize_command(svg_path | spec_path)
  → cached_pages() / render_preview_file()
    → _render_svg_preview()
      → [Playwright | CairoSVG | rsvg-convert | Inkscape]
    → raster_output_path()       [cache.py]
```

### Reconcile Pipeline
```
reconcile_command(edited_svg | --all)
  → cached_pages()               [cache.py]
  → parse_svg()                  [reconcile.parse]
  → diff_svgs()                   [reconcile.diff]
  → report_payload() / print_report() [reconcile.report]
  → reconcile_report_path()       [cache.py]
```

### Validation Pipeline
```
validate_command(spec_path)
  → resolve_spec_path()
  → load_dsl_module()
  → collection_from_module()
  → validate_document() for each document
```

### Check Pipeline
```
check_command(target)
  → resolve_check_target()       [check.target]
  → run_check()                  [check.runner]
    → validate + lint + format + typecheck backends
```

### Create Pipeline
```
create_command(target_dir)
  → _copy_template()             [importlib.resources]
    → _render_jinja()            [jinja2]
```

## Integration

- **Entry point**: `python -m folio` via `__main__.py` → `cli.py` → Typer app
- **Script entry**: `folio` console script via `pyproject.toml` → `folio.cli:app`
- **Depends on**: `folio.dsl`, `folio.cache`, `folio.preview`, `folio.check`, `folio.reconcile`, `folio.search`
- **Consumed by**: End users (CLI), CI/CD pipelines (check/build/reconcile)
- **Config**: `folio.config` is a reserved stub; actual config resolution lives in `dsl.loader` via `config_dir=`
