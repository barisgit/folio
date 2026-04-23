# src/folio/check/

## Responsibility
Provides a pluggable, multi-tool check pipeline for Folio build specs: validation, linting, formatting, and typechecking. Acts as the **Facade** layer over external tooling, abstracting backend availability and fallback chains behind a unified `run_check` entry point.

## Design Patterns

- **Facade / Adapter**: `Backend` protocol abstracts lint, format, and typecheck backends; each concrete backend (`RuffLintBackend`, `BlackFormatBackend`, `PyrightTypecheckBackend`, etc.) adapts an external CLI tool.
- **Strategy / Fallback Chain**: `LINT_BACKENDS`, `FORMAT_BACKENDS`, `TYPECHECK_BACKENDS` are ordered lists; `select_backend` returns the first available tool, skipping unavailable ones. This is a **Chain of Responsibility** pattern with fallback semantics.
- **Pipeline / Sequence**: `run_check` executes steps in strict order: validate → lint → (optional format) → typecheck. Each step is a `StepResult` that can halt the pipeline on failure.
- **Data Transfer Object (DTO)**: `BackendResult`, `StepResult`, `CheckResult`, `BackendSelection`, and `CheckTarget` are immutable dataclasses used for passing structured data between layers.
- **Protocol**: `Backend` is a `Protocol` class for structural subtyping of backend implementations.

## Data & Control Flow

1. `resolve_check_target(target)` resolves a CLI target path → `CheckTarget` (spec_path + project_root).
2. `run_check(target)` orchestrates the pipeline:
   - `run_validate(target)` — loads the DSL module via `load_dsl_module`, builds the document tree via `document_from_module`, and calls `validate_document`. Raises `DslError` or `RenderError` on failure. Halts pipeline on failure.
   - `_run_backend_step("lint", LINT_BACKENDS, target)` — `select_backend` picks first available lint backend; calls `backend.run(project_root, fix=fix, verbose=verbose)` → `BackendResult`.
   - `_run_backend_step("format", FORMAT_BACKENDS, target)` — skipped unless `fmt=True` or `fix=True`.
   - `_run_backend_step("typecheck", TYPECHECK_BACKENDS, target)` — always runs last.
3. `CheckResult` aggregates all `StepResult`s; exit code is computed via `result.exit_code` property (0 = pass, 1 = diagnostics found, 2 = infra failure/no backend).

### Backend execution flow
- Each backend runs a `subprocess.run` against the tool binary.
- Ruff-based backends use `--output-format json` and parse JSON diagnostics (`_summarise_ruff_json`, `_summarise_pyright_json`).
- Format backends count lines matching `"Would reformat"` / `"would reformat"` prefixes to report file counts.
- `BackendResult` is returned with `success`, `output`, `diagnostics_count`, `command`, and `backend_name`.

## Integration Points

- **Consumed by**: `folio.check` CLI command group (via `folio/commands/check.py`).
- **Depends on**:
  - `folio.dsl.loader` — `load_dsl_module`, `resolve_spec_path`
  - `folio.dsl.renderer` — `document_from_module`, `validate_document`, `RenderError`, `DslError`
  - External tools: `ruff`, `black`, `ty`, `pyright` (resolved at runtime via `shutil.which`)
- **Exports**: `run_check` (the primary public API via `__init__.py`).
