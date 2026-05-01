# Folio Services Layer — Code Map

## 1. Responsibility

The `folio.services` package provides **feature-level services** built on top of the core layer (`folio.core`). Each subdirectory implements a distinct capability:

| Subdirectory | Responsibility |
|---|---|
| `check/` | Multi-backend validation pipeline: Folio DSL validation, example execution, lint, format, typecheck |
| `docs/` | Static documentation index generation from DSL source (the `index.json` shipped with wheels) |
| `reconcile/` | SVG diffing: parse two SVGs and report structural/attribute changes between them |
| `search/` | Stock image and SVG icon search via third-party APIs (OpenVerse, Pexels, Pixabay, SVGL, Iconify, Simple Icons) |
| `tweaks_load.py` | Spec-load orchestrator that wires tweak persistence (`theme.toml`) into the DSL rendering pipeline |
| `playground.py` | Server-independent playground state serialization, cache-free playground rendering, tweak validation, and deterministic `theme.toml` update logic |
| `playground_server.py` | Stdlib `ThreadingHTTPServer` adapter for `GET /`, `GET /api/state`, and `PATCH /api/tweaks` |

The services layer does **not** own the DSL, rendering, or document models — those live in `folio.core`.

---

## 2. Design

### 2.1 `services/check/` — Backend Adapter + Pipeline Pattern

**Pattern: Strategy / Adapter + Sequential Pipeline**

```
CheckTarget (target.py)
       │
       ▼
  run_check()  ──►  Step 1: run_validate()
  (runner.py)   ──►  Step 2: run_examples()
                    Step 3: _run_backend_step("lint",  LINT_BACKENDS,   target)
                    Step 4: _run_backend_step("format", FORMAT_BACKENDS,  target)  [opt-in]
                    Step 5: _run_backend_step("typecheck", TYPECHECK_BACKENDS, target)
```

- `Backend` — `Protocol` defining `is_available()` and `run(project_root, *, fix, verbose) -> BackendResult`
- `BackendResult` — `frozen` dataclass: `success`, `output`, `backend_name`, `command`, `diagnostics_count`, `fixed_count`
- **Fallback chains**: `LINT_BACKENDS` → `RuffLintBackend`; `FORMAT_BACKENDS` → `RuffFormatBackend` → `BlackFormatBackend`; `TYPECHECK_BACKENDS` → `TyTypecheckBackend` → `PyrightTypecheckBackend`
- `select_backend(chain)` returns the first available backend, recording skipped ones
- `CheckResult` aggregates `StepResult` objects; exposes `ok`, `infra_failure`, `exit_code`
- Exit codes: `0` = pass, `1` = diagnostics, `2` = infra failure
- `CheckTarget` holds resolved `spec_path` and `project_root`

**Key classes / functions:**
- `backends.py`: `Backend` (Protocol), `BackendResult`, `BackendSelection`, `RuffLintBackend`, `RuffFormatBackend`, `BlackFormatBackend`, `TyTypecheckBackend`, `PyrightTypecheckBackend`, `select_backend()`, `LINT_BACKENDS`, `FORMAT_BACKENDS`, `TYPECHECK_BACKENDS`
- `runner.py`: `StepResult`, `CheckResult`, `run_validate(target)`, `run_examples(target)`, `_evaluate_example(symbol, example, index)`, `run_check(target, *, fmt, fix, verbose) -> CheckResult`
- `target.py`: `CheckTarget`, `resolve_check_target(target: Path | None) -> CheckTarget`

---

### 2.2 `services/docs/` — Documentation Index Generator

**Pattern: Discovery → Parsing → Serialization pipeline**

```
discover_all()            — walks 3 DSL surfaces, emits Symbol records
    │
    ▼
parse_docstring(raw)      — parses Google-style docstrings into ParsedDoc
    │
    ▼
build_index()             — assembles Index with version/timestamp
    │
    ▼
dumps(index)              — JSON serialization (schema.py provides to_dict())
```

**Three discovery surfaces:**
1. `folio.dsl.__all__` — modules → sub-modules (e.g. `tweaks`); callables/classes → `_describe_callable_or_class`
2. `folio.dsl.tokens.__all__` — tokens → `_describe_token` (scalars from `TOKEN_DOCS`, callables from docstring)
3. `folio.dsl.tokens.STYLES` — style presets → `_describe_style` (from `STYLE_DOCS`)

**Schema types** (`schema.py`):
- `Index` (version, generated_at, folio_version, symbols)
- `Symbol` (id, name, kind, module, signature, summary, description, params, returns, examples, tags, source)
- `Param`, `Returns`, `Example` — leaf types with `to_dict()`

**Kind enum**: `VALID_KINDS = ("primitive", "defs", "token", "style", "builder", "helper")`

**Kind registry** (`meta.py`): `DSL_KINDS: dict[str, str]` — maps every `folio.dsl.__all__` entry to its kind; tokens and styles are self-classifying

**Source resolution** (`source_info.py`):
- `resolve_source(obj) -> "module.path:lineno"` — uses `inspect.getsourcelines()` after `inspect.unwrap()` for re-export unwrapping
- `public_module_for(name) -> "folio.dsl"` — always returns the public import path

**Docstring parser** (`docstring_parser.py`):
- Parses Google-style: `Summary.\n\nDescription.\n\nArgs: ... Returns: ... Example: ... Tags: ...`
- Sections: `Args`/`Arguments`/`Parameters`, `Returns`/`Return`, `Example`/`Examples`, `Tags`
- Example caption extracted from leading `# ...` comment line
- `ParsedDoc(summary, description, params, returns_doc, examples, tags)`

**Key functions:**
- `discovery.py`: `discover_all() -> list[Symbol]`, `_iter_symbols()`, `_describe_*()` helpers, `_render_signature()`, `_require_parsed_doc()`, `_ensure_examples()`
- `generate.py`: `build_index() -> Index`, `index_path() -> Path`, `write_index(destination) -> Path`, `main(argv) -> int`
- `serialize.py`: `dumps(Index) -> str`, `loads(str) -> dict`
- `__main__.py`: forwards to `generate.main`; also reachable as `python -m folio.docs` or `folio docs generate`

---

### 2.3 `services/reconcile/` — SVG Diff Engine

**Pattern: Parse → Diff → Report**

```
parse_svg(path)           — SVG XML → ParsedSvg (using html.parser)
    │
    ▼
diff_svgs(base, edited)   — compare two ParsedSvg trees → DiffResult
    │
    ▼
report_payload / print_report — format DiffResult as dict or Rich output
```

**Parse stage** (`parse.py`):
- `_SvgTreeParser` — `HTMLParser` subclass; handles SVG namespace stripping, whitespace normalization, transform attribute normalization
- `ParsedElement(element_id, tag, text, attrs, parent_id)` — frozen dataclass per SVG element
- `ParsedSvg(path, page_number, elements: dict[id → ParsedElement])`
- Page number detection: first checks `data-page-number` attribute on root `<g>`, falls back to `detect_page_number(svg_path, elements)` → filename pattern `page{N}` or `p{N}`
- `ParseError` — raised on XML failure

**Diff stage** (`diff.py`):
- `_NUMERIC_ATTRS = {"cx","cy","font-size","height","r","width","x","x1","x2","y","y1","y2"}` — numeric comparison with pt↔mm conversion
- `_IGNORED_ATTRS = {"data-page-id","data-page-number","id","label"}` — always skipped
- `DiffResult(page_number, changes, warnings)` — changes are attribute-level diffs per element id
- `diff_svgs(base, edited) -> DiffResult`: shared ids → `_element_changes()`; added elements → `"added_element"` warning; deleted elements → `"deleted_element"` warning
- `_numeric_change(attr, old, new) -> dict` — produces both `_pt` and `_mm` keys
- `DiffError`

**Report stage** (`report.py`):
- `report_payload(result, base_svg, edited_svg, page_id) -> dict` — structured JSON payload
- `write_report(path, payload)` — writes JSON
- `print_report(payload)` — Rich console output with color coding
- `_warning_buckets()` — splits warnings into `added` / `removed` lists

---

### 2.4 `services/search/` — Stock + SVG Search Providers

**Pattern: Registry dispatch + graceful degradation**

```
fetch_stock(query, provider)         — single provider
fetch_stock_multi(query, providers)  — all providers, skip on failure

search_svg_assets(query, *, limit, sources)
    │
    ▼
  _search_svgl()       — api.svgl.app
  _search_iconify()    — api.iconify.design
  _search_simple_icons() — cdn.simpleicons.org/{slug}
    │
    ▼
  dedupe(results) → rank → verify → return SvgSearchResponse
```

**Stock image providers** (`providers.py`):
- `Provider = Literal["openverse", "pexels", "pixabay"]`
- `SearchResult(id, provider, description, url, thumbnail, width, height, license, creator, source)`
- `_fetch_openverse(query, per_page)` — no API key; paginates from `api.openverse.org/v1/images/`
- `_fetch_pexels(query, per_page)` — requires `PEXELS_API_KEY`
- `_fetch_pixabay(query, per_page)` — requires `PIXABAY_API_KEY`
- `_FETCHERS: dict[Provider, callable]` — registry map
- `fetch_stock_multi()` catches exceptions per-provider; raises `RuntimeError` only when **all** providers fail

**SVG icon providers** (`svg.py`):
- `SUPPORTED_SVG_SOURCES = ("svgl", "simple-icons", "iconify")`
- `SvgSearchResult(source, title, svg_url, subtitle, identifier, website, wordmark_url, verified)`
- `SvgSearchResponse(query, results, warnings)`
- Ranking: `(exact_match, contains_match, source_priority, title_key)` — lower is better
- `PREFERRED_ICONIFY_PREFIXES` — ordered priority: `logos`, `simple-icons`, `lucide`, `tabler`, `heroicons`, `ph`, `mdi`, `carbon`, `material-symbols`
- Verification: `_probe_svg_url()` — HEAD request with 512-byte snippet check for `<svg` or `<?xml`; auto-verifies `simple-icons` (CDN deterministic)
- `SvgSearchError` — raised for unknown sources or query validation failures

---

### 2.5 `tweaks_load.py` — Tweak Persistence + Spec Load Orchestrator

**Pattern: Context manager + validation-first load**

```
resolve_values_file(spec_path)       — locate <spec_dir>/theme.toml
       │
       ▼
load_persisted_values(values_path)   — parse TOML
       │
       ▼
tweak_context(registry):              — enter TweakRegistry context
    │
    ▼
  load_dsl_module(spec_path)         — DSL declarations register into registry
       │
    ▼
  validate_persisted_values(...)      — check TOML against declarations
       │
    ▼
  registry.apply_values(validated)    — apply validated TOML to registry
       │
    ▼
  collection_from_module(module)     — build DocumentCollection
       │
    ▼
  render_collection(collection, ...)  — render (or validate_document for validate_spec_with_tweaks)
```

- `TweakValidationError` — carries `Sequence[TweakDiagnostic]`; raised only on error-severity diagnostics
- `SpecLoadResult(result, snapshot, diagnostics)` — returned by `load_spec_with_tweaks(spec_path)`
- `SpecValidateResult(snapshot, diagnostics)` — returned by `validate_spec_with_tweaks(spec_path)`
- `load_spec_with_tweaks()` → renders via `render_collection()`
- `validate_spec_with_tweaks()` → validates via `validate_document()` (skips SVG rendering)

---

### 2.6 `playground.py` / `playground_server.py` — Local Tweak Playground

**Pattern: Service state model + stdlib HTTP adapter**

```
folio dev CLI
    │
    ▼
create_playground_server(spec)
    │
    ├─ load_playground_state(spec)       — render in `mode="playground"`, no cache writes
    │       ├─ load_spec_with_tweaks(..., render_mode="playground")
    │       ├─ serialize pages as PlaygroundPage
    │       └─ serialize declarations as PlaygroundTweak
    │
    └─ ThreadingHTTPServer + _PlaygroundRequestHandler
            ├─ GET /api/state     → serialize_playground_state(load_playground_state())
            └─ PATCH /api/tweaks  → debounced apply_tweak_update() + fresh state
```

- `PlaygroundPage`, `PlaygroundTweak`, `PlaygroundState`, `Diagnostic`, `TweakUpdateRequest` — Pydantic v2 `BaseModel` classes for the JSON-facing playground state model. Snake-case Python fields carry camelCase aliases (`spec_path → specPath`, `page_number → pageNumber`, `css_var → cssVar`, etc.) so `model_dump(mode="json", by_alias=True)` produces byte-for-byte the same wire format as the previous hand-rolled serializer. The Pydantic models are the single source of truth for the JSON contract; `src/folio/_dev/gen_playground_types.py` (excluded from wheels/sdists) projects them into `src/folio/playground_ui/api.generated.ts` so the Solid frontend gets matching TypeScript types.
- `load_playground_state(spec_path)` — renders in playground mode and returns pages, tweak declarations, resolved values, values path, and diagnostics without touching the last-build cache.
- `apply_tweak_update(spec_path, updates|key/value)` — rereads current `theme.toml`, validates proposed edits against current declarations, writes deterministic TOML, and returns a fresh state; invalid edits raise `PlaygroundUpdateError` without writing.
- `PlaygroundHTTPServer` — stdlib `ThreadingHTTPServer` bound to one spec path with startup state and an update debouncer.
- `_PlaygroundUpdateDebouncer` — coalesces rapid PATCH updates into one quiet-window persistence/render cycle so slider drags do not spam writes.
- `_PlaygroundRequestHandler` — serves embedded HTML, JSON state, and tweak updates; suppresses expected BrokenPipe/ConnectionReset disconnects from aborted browser requests.

---

## 3. Flow

### 3.1 `folio check` flow

```
CLI (src/folio/cli/check.py)
    │
    ▼
resolve_check_target(target_path)  → CheckTarget(spec_path, project_root)
    │
    ▼
run_check(target, fmt, fix, verbose)  → CheckResult
    │
    ├─── run_validate(target)
    │        load_dsl_module(spec_path)
    │        collection_from_module(module)
    │        validate_document(doc)  for doc in documents
    │
    ├─── run_examples(target)
    │        load index.json  (from docs package)
    │        exec every example code block  (via __builtins__["exec"])
    │
    ├─── _run_backend_step("lint",  LINT_BACKENDS,   target, fix, verbose)
    │        select_backend(LINT_BACKENDS)  → first available
    │        backend.run(project_root, fix=False, verbose)
    │
    ├─── [optional] _run_backend_step("format", FORMAT_BACKENDS, target, fix, verbose)
    │        select_backend(FORMAT_BACKENDS)
    │        backend.run(project_root, fix=fix, verbose)
    │
    └─── _run_backend_step("typecheck", TYPECHECK_BACKENDS, target, fix=False, verbose)
             select_backend(TYPECHECK_BACKENDS)
             backend.run(project_root, fix=False, verbose)

CheckResult  →  exit_code (0/1/2)  →  CLI exit
```

### 3.2 `folio docs generate` flow

```
python -m folio.docs.generate   (or: folio docs generate)
    │
    ▼
main(argv)  →  write_index()  →  build_index()  →  discover_all()
    │
    ▼
discover_all()
    │
    ├─── _iter_dsl_all(dsl)         — modules + callables from folio.dsl.__all__
    ├─── _iter_tokens_surface()      — tokens from folio.dsl.tokens.__all__
    └─── _iter_styles_surface()     — STYLES from folio.dsl.tokens.STYLES
    │
    ▼ (for each symbol)
parse_docstring(raw_docstring)  →  ParsedDoc
_render_signature(value)         →  (signature, params, returns_annotation)
resolve_source(value)           →  "module:lineno"
    │
    ▼
Index(version=INDEX_SCHEMA_VERSION, generated_at, folio_version, symbols)
    │
    ▼
dumps(index)  →  JSON  →  index.json  (committed in repo)
```

### 3.3 `folio reconcile` flow

```
CLI (src/folio/cli/reconcile.py)
    │
    ▼
parse_svg(base_path)   →  ParsedSvg
parse_svg(edited_path) →  ParsedSvg
    │
    ▼
diff_svgs(base, edited)  →  DiffResult
    │
    ▼
report_payload(result, base_svg, edited_svg, page_id)
    │
    ▼
write_report(output_path, payload)   — if --output FILE
print_report(payload)              — always to console
```

### 3.4 `folio search` flow (stock)

```
CLI (src/folio/cli/search.py)
    │
    ▼
fetch_stock(query, provider)          — single provider, raises on missing key
       OR
fetch_stock_multi(query, providers)   — all providers, graceful degradation
    │
    ▼
_http_get_json(url, headers)          — urllib.request (stdlib only)
    │
    ▼
SearchResult list  →  CLI renders as table
```

### 3.5 `folio search svg` flow

```
CLI
    │
    ▼
search_svg_assets(query, limit, sources)
    │
    ├─── _search_svgl(query, limit)          — api.svgl.app  →  list[SvgSearchResult]
    ├─── _search_simple_icons(query, limit)  — cdn.simpleicons.org/{slug}
    │        _probe_svg_url(svg_url)          — HEAD check + snippet validation
    └─── _search_iconify(query, limit)        — api.iconify.design
    │
    ▼
dedupe_results(results)
    │
    ▼
rank_results(results, query)  — exact > contains > source_priority > title
    │
    ▼
_verify_results(results, limit)  — probe unverified URLs
    │
    ▼
SvgSearchResponse  →  CLI renders results
```

---

## 4. Integration

### 4.1 Dependencies on Core Layer

| Service | Imports from `folio.core` |
|---|---|
| `check/target.py` | `folio.core.dsl.loader.resolve_spec_path` |
| `check/runner.py` | `folio.core.dsl.loader` (`DslError`, `load_dsl_module`), `folio.core.render.pipeline` (`RenderError`, `collection_from_module`, `validate_document`) |
| `check/runner.py` (examples) | `folio.services.docs.generate.index_path` |
| `tweaks_load.py` | `folio.core.dsl.loader` (`DslError`, `load_dsl_module`), `folio.core.dsl.tweak_values`, `folio.core.dsl.tweaks`, `folio.core.render.pipeline` |
| `playground.py` | `folio.core.dsl.tweak_values`, `folio.core.dsl.tweaks`, `folio.services.tweaks_load.load_spec_with_tweaks` |
| `playground_server.py` | `folio.services.playground` state/update functions; stdlib `http.server` only for serving |
| `reconcile/diff.py` | `folio.core.render.primitives.pt_to_mm` |
| `docs/discovery.py` | `folio` (dsl module itself, introspected at runtime) |
| `docs/generate.py` | `folio.services.docs.discovery.discover_all`, `folio.services.docs.schema.Index`, `folio.services.docs.serialize.dumps` |

### 4.2 Consumed by CLI Layer

| CLI Command | Service Used |
|---|---|
| `folio check` | `folio.services.check.run_check`, `folio.services.check.resolve_check_target` |
| `folio docs generate` | `folio.services.docs.generate.main`, `folio.services.docs.generate.write_index` |
| `folio reconcile` | `folio.services.reconcile.parse.parse_svg`, `folio.services.reconcile.diff.diff_svgs`, `folio.services.reconcile.report.report_payload`, `folio.services.reconcile.report.print_report`, `folio.services.reconcile.report.write_report` |
| `folio search` (stock) | `folio.services.search.fetch_stock`, `folio.services.search.fetch_stock_multi`, `folio.services.search.PROVIDERS` |
| `folio search svg` | `folio.services.search.svg.search_svg_assets`, `folio.services.search.svg.SvgSearchResponse`, `folio.services.search.svg.SUPPORTED_SVG_SOURCES` |
| `folio validate` / `folio build` | `folio.services.tweaks_load.load_spec_with_tweaks`, `folio.services.tweaks_load.validate_spec_with_tweaks`, `folio.services.tweaks_load.TweakValidationError` |
| `folio dev` | `folio.services.playground_server.create_playground_server`, `folio.services.playground_server.playground_url`; handlers call `folio.services.playground.load_playground_state` and `apply_tweak_update` |

### 4.3 Package Public API (`__init__.py` exports)

| File | `__all__` |
|---|---|
| `services/__init__.py` | *(none — package doc only)* |
| `services/check/__init__.py` | `run_check` |
| `services/docs/__init__.py` | `Example`, `Index`, `Param`, `Returns`, `Symbol`, `VALID_KINDS` |
| `services/reconcile/__init__.py` | *(empty)* |
| `services/search/__init__.py` | `PROVIDERS`, `Provider`, `SearchResult`, `fetch_stock`, `fetch_stock_multi` |
| `services/tweaks_load.py` | `SpecLoadResult`, `SpecValidateResult`, `TweakValidationError`, `load_spec_with_tweaks`, `validate_spec_with_tweaks` |
| `services/playground.py` | `Diagnostic`, `PlaygroundPage`, `PlaygroundState`, `PlaygroundTweak`, `PlaygroundUpdateError`, `TweakUpdateRequest`, `apply_tweak_update`, `load_playground_state` |
| `services/playground_server.py` | `PlaygroundHTTPServer`, `create_playground_server`, `playground_url`, `serialize_playground_state` |

---

## File Index

```
src/folio/services/
├── __init__.py
├── codemap.md                          ← this file
├── playground.py                       ← cache-free playground state + tweak persistence service
├── playground_server.py                ← stdlib HTTP API + embedded playground shell
├── tweaks_load.py                      ← tweak persistence + spec load orchestrator
├── check/
│   ├── __init__.py                     ← exports run_check
│   ├── backends.py                     ← Backend Protocol, 5 backend adapters, select_backend()
│   ├── runner.py                       ← CheckResult, run_check(), run_validate(), run_examples()
│   └── target.py                       ← CheckTarget, resolve_check_target()
├── docs/
│   ├── __init__.py                     ← re-exports schema types
│   ├── __main__.py                     ← entry point: python -m folio.docs
│   ├── discovery.py                    ← discover_all(), _describe_*(), symbol iterators
│   ├── docstring_parser.py             ← parse_docstring(), ParsedDoc, Google-style parser
│   ├── generate.py                     ← build_index(), write_index(), index_path(), main()
│   ├── meta.py                         ← DSL_KINDS, TOKEN_DOCS, STYLE_DOCS, DEFAULT_EXAMPLE_SETUP
│   ├── schema.py                       ← Index, Symbol, Param, Returns, Example, VALID_KINDS
│   ├── serialize.py                   ← dumps(), loads() — JSON round-trip
│   └── source_info.py                  ← resolve_source(), public_module_for()
├── reconcile/
│   ├── __init__.py                     ← empty
│   ├── diff.py                         ← diff_svgs(), DiffResult, DiffError
│   ├── parse.py                        ← parse_svg(), ParsedSvg, ParsedElement, ParseError
│   └── report.py                       ← report_payload(), write_report(), print_report()
└── search/
    ├── __init__.py                     ← re-exports providers + SearchResult
    ├── providers.py                    ← fetch_stock(), fetch_stock_multi(), SearchResult, stock fetchers
    └── svg.py                          ← search_svg_assets(), SvgSearchResult, SvgSearchResponse, SVG fetchers
```
