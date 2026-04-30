# Repository Atlas: folio

## Project Responsibility
Python DSL SVG page builder and reconciliation CLI. Provides a Pythonic API for composing SVG documents with charts, icons, text, approved design-time tweaks, and a local browser tweak playground, plus a Typer-based CLI for building, previewing, validating, reconciling, and tuning SVG output. Uses a layered architecture: core domain → services → CLI, with protocol-based interfaces at layer boundaries.

## System Entry Points
- `src/folio/__main__.py`: Package entry point (`python -m folio` → Typer CLI).
- `src/folio/cli/dev.py`: Local `folio dev` tweak playground server command.
- `src/folio/__init__.py`: Package root, exposes `__version__`.
- `src/folio/dsl/__init__.py`: Public DSL API facade, re-exports from `core.dsl`.
- `src/folio/layout/__init__.py`: Public layout API facade, re-exports from `core.layout`.
- `pyproject.toml`: Dependency manifest (jinja2, rich, typer), Hatchling build config.

## Directory Map (Aggregated)
| Directory | Responsibility Summary | Detailed Map |
|-----------|------------------------|--------------|
| `src/folio/core/` | Domain model (immutable dataclasses), DSL authoring API, SVG rendering pipeline with build/playground render modes, export pipeline (PNG/PDF/IDML), geometric layout helpers, caching, and preview rasterization. | [View Map](src/folio/core/codemap.md) |
| `src/folio/cli/` | Typer CLI layer: 7 flat commands + 3 sub-apps (search, docs, skill). Pure orchestration — zero business logic. | [View Map](src/folio/cli/codemap.md) |
| `src/folio/services/` | Business logic services: check pipeline (ruff/black/pyright), docs generation from docstrings, SVG reconciliation/diff, multi-source image/icon search, tweak/spec loading, and the local playground state/server layer. | [View Map](src/folio/services/codemap.md) |
| `src/folio/interfaces/` | Runtime-checkable protocols (Builder, Renderer, Exporter, SearchProvider) defining contracts between layers. | [View Map](src/folio/interfaces/codemap.md) |
| `src/folio/skill/` | Bundled Claude Code skill: asset discovery and installation for the `folio skill install` command. | [View Map](src/folio/skill/codemap.md) |
| `src/folio/dsl/` | Thin re-export facade over `core.dsl`. Public API surface for DSL authoring. | — |
| `src/folio/layout/` | Thin re-export facade over `core.layout`. Public API surface for geometric helpers. | — |
| `src/folio/vendor/` | Vendored third-party libraries (qrcodegen.py). | — |
| `src/folio/templates/` | Jinja2 starter project scaffolding for `folio create`. | — |
| `src/folio/` | Package root: version, config stub, CLI entry point, layer orchestration. | [View Map](src/folio/codemap.md) |
