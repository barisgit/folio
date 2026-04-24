# src/

## Responsibility

Package root directory for the `folio` Python project. Contains the `folio/` sub-package which implements the entire DSL, CLI, rendering, and reconciliation system.

## Layout

- `folio/` — Main package (see [folio/codemap.md](folio/codemap.md))

## Design

Single-package layout with a flat `src/` directory. The `folio/` package is exposed via the `src/` path and is registered as a Hatchling package (`[tool.hatch.build.targets.wheel] packages = ["src/folio"]`).

## Entry Points

- `folio/__main__.py` — Enables `python -m folio` invocation; delegates to `cli.app`.
- `folio/cli.py` — Typer-based CLI root (`folio` command group). Registers all subcommands: `build`, `create`, `validate`, `rasterize`, `reconcile`, `check`, and the `search` sub-app.
- `folio/config.py` — Reserved compatibility module for project-specific config helpers.

## Integration

- Consumed by: `pyproject.toml` build config (Hatchling wheel/sdist packaging), `python -m` module invocation
- Contains: The entire application codebase
