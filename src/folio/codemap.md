# src/folio/

## Responsibility
Root package for the Folio DSL page builder. Provides version info, CLI entry point, and re-exports the public DSL API. Orchestrates a layered architecture: `core/` (domain), `services/` (business logic, including tweak playground state/server services), `cli/` (commands), `interfaces/` (protocols).

## Design
- **Layered architecture**: core → services → cli, with interfaces defining protocols for each layer boundary.
- **Facade re-exports**: `folio.dsl` and `folio.layout` are thin re-export facades over `folio.core.dsl` and `folio.core.layout` respectively.
- `__init__.py` exposes only `__version__ = "0.1.0"`.
- `__main__.py` delegates to `folio.cli.app` for `python -m folio` invocation.
- `config.py` is a stub reserved for future project-specific config helpers.
- `vendor/` bundles third-party code (qrcodegen.py) to avoid external dependencies.
- `templates/starter/` contains Jinja2 project scaffolding for `folio create`.

## Flow
1. `python -m folio` → `__main__.py` → `cli.app()` (Typer)
2. `folio dev <spec>` → CLI resolves `build.py`, starts a local stdlib playground server, renders in playground mode, and persists approved tweaks to `theme.toml`
3. DSL usage: `from folio.dsl import rect, text, tweaks, ...` → re-exported from `core.dsl`
4. Layout usage: `from folio.layout import Columns, Grid, ...` → re-exported from `core.layout`

## Integration
- **Depends on**: `cli/`, `core/`, `services/`, `interfaces/`, `skill/`, `vendor/`
- **Consumed by**: End users via CLI or DSL imports
- **Public API surface**: `folio.dsl.*` (DSL authoring), `folio.layout.*` (geometric helpers)

### Subdirectory Map
| Directory | Responsibility | Codemap |
|-----------|---------------|---------|
| `core/` | Domain model, DSL, rendering, export, layout | [core/codemap.md](core/codemap.md) |
| `cli/` | Typer CLI commands | [cli/codemap.md](cli/codemap.md) |
| `services/` | Business logic services (check, docs, reconcile, search, tweaks, playground state/server) | [services/codemap.md](services/codemap.md) |
| `interfaces/` | Runtime-checkable protocols (Builder, Renderer, Exporter, SearchProvider) | [interfaces/codemap.md](interfaces/codemap.md) |
| `skill/` | Bundled Claude Code skill asset management | [skill/codemap.md](skill/codemap.md) |
| `vendor/` | Vendored third-party libraries (qrcodegen) | — |
| `templates/` | Jinja2 starter project scaffolding | — |
