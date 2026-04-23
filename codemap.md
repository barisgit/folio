# Repository Atlas: folio

## Project Responsibility
Python DSL SVG page builder and reconciliation CLI. Provides a Pythonic API for composing SVG documents with charts, icons, and text, plus a Typer-based CLI for building, previewing, validating, and reconciling SVG output.

## System Entry Points
- `src/folio/cli.py`: Typer CLI app with 7 subcommands (build, create, validate, preview, reconcile, check, search).
- `src/folio/__main__.py`: Package entry point (`python -m folio`).
- `src/folio/__init__.py`: Package root, exposes `__version__`.
- `pyproject.toml`: Dependency manifest (jinja2, rich, typer), Hatchling build config.

## Directory Map (Aggregated)
| Directory | Responsibility Summary | Detailed Map |
|-----------|------------------------|--------------|
| `src/folio/dsl/` | Builder + immutable model + SVG renderer pipeline. Defines Python DSL types, ChartHandle API, word-wrap algorithm, DefNode composition. | [View Map](src/folio/dsl/codemap.md) |
| `src/folio/commands/` | 7 CLI command adapters wrapping Typer. Each command orchestrates a sub-system. | [View Map](src/folio/commands/codemap.md) |
| `src/folio/check/` | Pluggable check pipeline (validate → lint → format → typecheck) as a Facade over external tools (ruff, black, ty, pyright). | [View Map](src/folio/check/codemap.md) |
| `src/folio/reconcile/` | SVG diff engine: parses SVG via HTMLParser, computes set-based diff, formats JSON or rich terminal output. | [View Map](src/folio/reconcile/codemap.md) |
| `src/folio/render/` | Stateless SVG primitive layer: converts typed geometric/textual data into SVG XML strings with memoized data URI embedding. | [View Map](src/folio/render/codemap.md) |
| `src/folio/layout/` | Frozen dataclass layout helpers: Columns (1D), Grid (2D row-major), FlowColumns (panel + arrow lanes). Pure math, no folio deps. | [View Map](src/folio/layout/codemap.md) |
| `src/folio/search/` | Multi-source search: OpenVerse/Pexels/Pixabay for stock images; SVGL/simple-icons/Iconify for SVG icons with live URL probing. | [View Map](src/folio/search/codemap.md) |
| `src/folio/` | Root package: CLI app, config loader, cache layer, preview rasterizer. | [View Map](src/folio/codemap.md) |
| `src/` | Package root with Hatchling build config. | [View Map](src/codemap.md) |
