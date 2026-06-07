# Folio CLI — Code Map

## 1. Responsibility

The CLI layer (`src/folio/cli/`) is a pure **IO adapter layer** — zero business logic lives here. Every command:

1. Parses CLI arguments via **Typer** annotations
2. Delegates to the **engine/service layer** (`folio.core`, `folio.services`)
3. Formats and renders output via **Rich** console

Commands are wired into a single `typer.Typer` app (`app`) exported from `cli/__init__.py`. Sub-command groups (`search`, `docs`, `skill`) use `typer.Typer` sub-apps registered via `app.add_typer()`. The flat command set includes `folio dev`, which is the CLI adapter for the local tweak playground.

---

## 2. Design

### Root App (`app`)

**File:** `src/folio/cli/__init__.py`

- `app: typer.Typer` — root application, registered as `__all__ = []`
- Global `--version`/`-V` option via `@app.callback()` with `version_callback()`
- Version resolved from `importlib.metadata.version("folio-dsl")`
- Registered commands:

| Registration | Source |
|---|---|
| `app.command("build")(build_command)` | `cli/build.py` |
| `app.command("create")(create_command)` | `cli/create.py` |
| `app.command("dev")(dev_command)` | `cli/dev.py` |
| `app.command("validate")(validate_command)` | `cli/validate.py` |
| `app.command("rasterize")(rasterize_command)` | `cli/rasterize.py` |
| `app.command("reconcile")(reconcile_command)` | `cli/reconcile.py` |
| `app.command("check")(check_command)` | `cli/check.py` |
| `app.add_typer(search_app, name="search")` | `cli/search/__init__.py` |
| `app.add_typer(docs_app, name="docs")` | `cli/docs.py` |
| `app.add_typer(skill_app, name="skill")` | `cli/skill.py` |

### Sub-App Patterns

- `docs_app`, `skill_app`: `typer.Typer` instances, exposed as `__all__ = ["docs_app"]` / `__all__ = ["skill_app"]`
- `search_app`: also exports `app` alias; re-exports `fetch_stock`, `fetch_stock_multi`, `search_svg_assets` for external use

### Exit Codes Convention

| Exit Code | Meaning |
|---|---|
| 0 | Success |
| 1 | User error / validation failure |
| 2 | Render/cache error |
| 3 | Reconcile detected changes |

---

## 3. Flow

### `folio build` → `build_command()`

```
args + --out-dir/--page/--no-cache
    │
    ├─ resolve_spec_path(spec_path?)        → Path
    ├─ load_spec_with_tweaks(spec)          → Outcome[SpecResult]
    ├─ reject_unknown_collection_targets()  ← filters targets
    ├─ plan_export_targets(doc, targets)    → ExportPlan
    ├─ reject_page_with_document_targets()  ← filters by --page
    ├─ filter_result_by_page()             → SpecResult
    ├─ execute_export_plan(doc, plan, out)  → list[Path]
    └─ cache_build(result) if not --no-cache → CacheInfo
```

Key imports from `folio.core`:
- `cache_build`, `last_build_svg`, `cached_pages` — `folio.core.cache`
- `resolve_spec_path`, `DslError` — `folio.core.dsl.loader`
- `TweakValuesError` — `folio.core.dsl.tweak_values`
- `execute_export_plan`, `plan_export_targets` — `folio.core.export.pipeline`
- `document_requested_targets`, `filter_result_by_page`, `reject_page_with_document_targets`, `reject_unknown_collection_targets` — `folio.core.export.targets`
- `RenderError` — `folio.core.render.pipeline`
- `load_spec_with_tweaks`, `TweakValidationError` — `folio.services.tweaks_load`

### `folio dev` → `dev_command()`

```
spec_path? + --host/--port/--open/--no-open
    │
    ├─ resolve_spec_path(spec_path?)                 → Path
    ├─ create_playground_server(resolved, host, port) → PlaygroundHTTPServer
    │       ├─ load_playground_state(spec)            → startup render, cache-free
    │       └─ bind ThreadingHTTPServer to spec path
    ├─ playground_url(server)                         → stdout URL
    ├─ webbrowser.open(url) if --open                 → best-effort convenience
    └─ server.serve_forever() until KeyboardInterrupt
```

Key imports: `resolve_spec_path`, `DslError`; `create_playground_server`, `playground_url`; `PlaygroundUpdateError`; `TweakValuesError`, `TweakValidationError`; `RenderError`. The command remains an IO adapter: server state, HTTP endpoints, validation, and persistence live under `folio.services.playground*`.

### `folio validate` → `validate_command()`

```
spec_path? (default: cwd lookup)
    │
    └─ validate_spec_with_tweaks(resolved_spec) → Outcome
            │
            ├─ TweakValuesError   → exit(1)
            ├─ TweakValidationError → exit(1) with per-diagnostic output
            └─ DslError, RenderError → exit(1)
```

Same tweak/diagnostic flow as build; no rendering, no cache.

### `folio rasterize` → `rasterize_command()`

```
svg_path? + --spec/--output/--viewport
    │
    ├─ If svg_path given:
    │       render_preview_file(svg, output_path, viewport) → Path
    └─ Else (batch from cache):
            cached_pages(spec) → iter PageInfo
            for each page:
                last_build_svg(spec, page_num) → Path
                render_raster(svg, spec, page_num, viewport) → Path
```

Key imports: `cached_pages`, `last_build_svg` from `folio.core.cache`; `resolve_spec_path` from `folio.core.dsl.loader`; `render_preview_file`, `render_raster`, `PreviewError` from `folio.core.preview`; `CacheError` from `folio.core.cache`.

### `folio reconcile` → `reconcile_command()`

```
edited_svg? + --all/--edited-dir/--page/--spec/--format
    │
    ├─ If --all:
    │       iter cached_pages(spec)
    │       for each page: _reconcile_one(spec, candidate, page_number=page.page_number)
    └─ Else:
            _reconcile_one(spec, edited_svg, page_number=page_number)
                    │
                    ├─ parse_svg(edited)  → ParsedSvg
                    ├─ last_build_svg(spec, page_num) → Path
                    ├─ parse_svg(base)     → ParsedSvg
                    ├─ diff_svgs(base, edited) → DiffResult
                    ├─ report_payload(result, ...)
                    ├─ write_report(report_path, payload)
                    └─ return (payload, has_changes)

output: print_report(payload) or JSON dump → exit(3) if changes detected
```

Key imports: `cached_pages`, `last_build_svg`, `reconcile_report_path`, `CacheError` from `folio.core.cache`; `resolve_spec_path` from `folio.core.dsl.loader`; `diff_svgs` from `folio.services.reconcile.diff`; `parse_svg`, `ParsedSvg`, `ParseError` from `folio.services.reconcile.parse`; `print_report`, `report_payload`, `write_report` from `folio.services.reconcile.report`.

Helper `_page_id(parsed: ParsedSvg) → str | None` extracts `data-page-id` attribute from top-level `<g>` or any element.

### `folio check` → `check_command()`

```
target? + --format/--fix/--verbose
    │
    ├─ resolve_check_target(target) → CheckTarget
    ├─ run_check(target, fmt, fix, verbose) → CheckResult
    └─ _format_summary(verbose, result) → str
            for step in result.steps:
                status symbol, backend name, command (if verbose),
                skipped_backends (if verbose), output lines (if verbose)
```

Key imports: `CheckResult`, `run_check` from `folio.services.check.runner`; `resolve_check_target` from `folio.services.check.target`.

### `folio create` → `create_command()`

```
target_dir + --var/--no-skill
    │
    ├─ _parse_vars(var_args) → dict[str, str]
    ├─ _default_project_slug(target_dir) → str (from directory name)
    ├─ _builtin_template_root() → Traversable (folio/templates/starter)
    ├─ _copy_template(source, target_dir, vars)
    │       recursively copies, strips .j2/.jinja/.jinja2 suffix,
    │       renders via Jinja2 StrictUndefined
    │       skips: __pycache__, .pytest_cache, .ruff_cache, .mypy_cache,
    │               .ty_cache, .venv, out, .cache, *.pyc, *.pyo, template.yaml
    └─ _install_starter_skill(target_dir)
            copies skill_assets() → target_dir/.agents/skills/folio/
```

Key imports: `resources.files("folio")` (importlib.resources); `skill_assets`, `skill_root` from `folio.skill`; `shutil.copy2`.

### `folio search stock` → `stock_command()`

```
query + --provider/--per-page/--json
    │
    ├─ _resolve_providers(provider_list?)
    │       default: ["openverse"]; "all" expands to all PROVIDERS
    │       validates against PROVIDERS tuple; raises RuntimeError on unknown
    ├─ fetch_stock(query, provider, per_page)  [single provider]
    │       or
    │   fetch_stock_multi(query, providers, per_page)  [multi-provider]
    │       from folio.services.search.providers
    └─ _render_table(results) or _render_json(results)
```

`PROVIDERS` and `Provider` type imported from `folio.services.search.providers`. `SearchResult` dataclass has fields: `id`, `provider`, `description`, `url`, `thumbnail`, `width`, `height`, `license`, `creator`, `source`.

### `folio search svg` → `svg_command()`

```
query + --limit/--source/--json
    │
    ├─ search_svg_assets(query, limit, sources=tuple) → SvgSearchResponse
    │       from folio.services.search.svg
    └─ _render_results_table(response) or JSON
```

`SUPPORTED_SVG_SOURCES` and `SvgSearchError` also imported from `folio.services.search.svg`. `SvgSearchResponse` has `.results` (list) and `.warnings` (list). Individual results have `source`, `title`, `subtitle`, `identifier`, `website`, `svg_url`.

### `folio docs show` → `show_command()`

```
symbol + --format/--json
    │
    ├─ _load_index() → dict (validated version==1, FileNotFoundError, JSONDecodeError)
    ├─ _find_symbol(index, symbol) → dict|None
    │       exact id match → bare name fallback
    ├─ _nearest_symbol(index, symbol) → str|None (difflib.get_close_matches, cutoff=0.55)
    └─ _render_symbol_text(symbol) or _symbol_to_markdown() or _print_json()
```

Index loaded from `folio.services.docs.generate.index_path()`. Exits with codes: `_EXIT_NOT_FOUND` (2), `_EXIT_USER_ERROR` (1), `_EXIT_SCHEMA_MISMATCH` (3).

Renders via `rich.console.Console`, `rich.markdown.Markdown`, `rich.panel.Panel`, `rich.table.Table`. Symbol dict keys: `id`, `name`, `kind`, `signature`, `summary`, `description`, `params` (list of `name`/`type`/`doc`), `returns` (`type`/`doc`), `examples` (list of `caption`/`code`), `tags`, `source`, `module`.

### `folio docs search` → `search_command()`

Matches against: `name`, `summary`, `tags` (space-joined), and each param `name`. Case-insensitive substring search. Outputs via `_render_search_text()` (table), `_search_to_markdown()`, or JSON.

### `folio docs list` → `list_command()`

```
--kind? + --format/--json
    │
    └─ filter index["symbols"] by kind (validated against VALID_KINDS)
```

`VALID_KINDS` imported from `folio.services.docs`.

### `folio docs generate` → `generate_command()`

Calls `folio.services.docs.generate.main([])` and exits with its return code.

### `folio skill install` → `install_command()`

```
--scope (user|project) + --force
    │
    ├─ _resolve_destination(scope) → Path
    │       user: ~/.../skills/folio
    │       project: ./.../skills/folio
    ├─ _conflicting_files(source, dest, assets) → list[Path]
    │       compares byte content
    ├─ _install_skill(destination, force) → int
    │       mkdir -p, shutil.copy2 each asset
    └─ raise typer.Exit(code=exit_code)
```

Key imports: `skill_assets`, `skill_root` from `folio.skill`.

---

## 4. Integration

### Imports from `folio.core`

| File | Imports |
|---|---|
| `build.py` | `cache_build` (cache), `resolve_spec_path` (dsl.loader), `TweakValuesError` (dsl.tweak_values), `execute_export_plan`, `plan_export_targets` (export.pipeline), `document_requested_targets`, `filter_result_by_page`, `reject_page_with_document_targets`, `reject_unknown_collection_targets` (export.targets), `RenderError` (render.pipeline), `load_spec_with_tweaks`, `TweakValidationError` (services.tweaks_load) |
| `validate.py` | `resolve_spec_path` (dsl.loader), `DslError`, `TweakValuesError` (dsl.tweak_values), `RenderError` (render.pipeline), `validate_spec_with_tweaks`, `TweakValidationError` (services.tweaks_load) |
| `rasterize.py` | `CacheError`, `cached_pages`, `last_build_svg` (cache), `resolve_spec_path` (dsl.loader), `PreviewError`, `render_preview_file`, `render_raster` (preview) |
| `reconcile.py` | `CacheError`, `cached_pages`, `last_build_svg`, `reconcile_report_path` (cache), `resolve_spec_path` (dsl.loader) |

### Imports from `folio.services`

| File | Imports |
|---|---|
| `build.py` | `load_spec_with_tweaks`, `TweakValidationError` (`tweaks_load`) |
| `validate.py` | `validate_spec_with_tweaks`, `TweakValidationError` (`tweaks_load`) |
| `check.py` | `CheckResult`, `run_check` (`check.runner`), `resolve_check_target` (`check.target`) |
| `reconcile.py` | `diff_svgs` (`reconcile.diff`), `parse_svg`, `ParsedSvg`, `ParseError` (`reconcile.parse`), `print_report`, `report_payload`, `write_report` (`reconcile.report`) |
| `docs.py` | `VALID_KINDS` (`docs`), `index_path`, `main` as `_generate_main` (`docs.generate`) |
| `search/stock.py` | `PROVIDERS`, `Provider`, `SearchResult`, `fetch_stock`, `fetch_stock_multi` (`search.providers`) |
| `search/svg.py` | `SUPPORTED_SVG_SOURCES`, `SvgSearchError`, `SvgSearchResponse`, `search_svg_assets` (`search.svg`) |

### Imports from `folio.skill`

| File | Imports |
|---|---|
| `create.py` | `skill_assets`, `skill_root` |
| `skill.py` | `skill_assets`, `skill_root` |

### Shared Patterns

- **Console**: `from rich.console import Console` — `console = Console()` in all files that print
- **Error console**: `from rich.console import Console` as `_error_console = Console(stderr=True)` in `docs.py`, `skill.py`
- **Typer**: `Annotated[..., typer.Argument/Option(...)]` for all arguments; `typer.BadParameter` for argument validation errors
- **Exit**: `raise typer.Exit(code=N)` — never `sys.exit` directly
- **No business logic**: All spec loading, rendering, diffing, searching, caching happens in `core`/`services`; CLI only orchestrates calls and formats output
