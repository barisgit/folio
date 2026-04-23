# Capability: Check Pipeline

## Purpose

Describe Folio's project-level validation, lint, formatting, and typecheck workflow.

## Requirements

### Requirement: Check target resolution
Folio SHALL resolve a check target into both a spec path and a project root.

#### Scenario: No explicit target
- **WHEN** a user runs `folio check` with no argument
- **THEN** Folio treats the current working directory as the project root
- **AND** resolves the spec path to `./build.py`

#### Scenario: Directory target
- **WHEN** a user passes a directory to `folio check`
- **THEN** Folio treats that directory as the project root
- **AND** resolves the spec path to `<directory>/build.py`

#### Scenario: File target
- **WHEN** a user passes a spec file to `folio check`
- **THEN** Folio treats that file as the spec path
- **AND** uses the file's parent directory as the project root

### Requirement: Check pipeline order
Folio SHALL run checks in the order validate, lint, optional format, then typecheck.

#### Scenario: Validation gates later steps
- **WHEN** validation fails
- **THEN** Folio stops the pipeline immediately
- **AND** does not run lint, format, or typecheck steps

#### Scenario: Format participation
- **WHEN** a user passes `--format`
- **THEN** Folio inserts a formatting step after lint and before typecheck

#### Scenario: Fix implies format
- **WHEN** a user passes `--fix`
- **THEN** Folio enables the format step even if `--format` was not passed explicitly
- **AND** forwards fix mode to the lint and format backends that support it

### Requirement: Backend fallback chains
Folio SHALL use the first available backend in each configured fallback chain.

#### Scenario: Availability-based fallback
- **WHEN** Folio selects a backend from a fallback chain
- **THEN** it falls back only when a preferred backend is unavailable
- **AND** it does not switch to another backend merely because the selected backend reported diagnostics

#### Scenario: Lint backend selection
- **WHEN** linting is requested
- **THEN** Folio uses Ruff as the lint backend

#### Scenario: Format backend selection
- **WHEN** formatting is requested
- **THEN** Folio prefers Ruff Format
- **AND** falls back to Black when Ruff Format is unavailable

#### Scenario: Typecheck backend selection
- **WHEN** typechecking is requested
- **THEN** Folio prefers `ty`
- **AND** falls back to Pyright when `ty` is unavailable

#### Scenario: Missing backend chain
- **WHEN** no backend in a required chain is available
- **THEN** Folio reports an infrastructure failure for that step

### Requirement: Check exit semantics
Folio SHALL expose stable exit codes for passing runs, diagnostics, and infrastructure failures.

#### Scenario: Passing run
- **WHEN** all executed steps succeed
- **THEN** `folio check` exits with status code `0`

#### Scenario: Diagnostics found
- **WHEN** validation, lint, format, or typecheck reports project issues
- **THEN** `folio check` exits with status code `1`

#### Scenario: Tooling infrastructure failure
- **WHEN** Folio cannot run a required backend because no suitable tool is available
- **THEN** `folio check` exits with status code `2`

### Requirement: Concise default output
Folio SHALL keep normal CLI output concise and only show backend commands/details in verbose mode.

#### Scenario: Default output
- **WHEN** `folio check` succeeds without `--verbose`
- **THEN** the CLI prints concise per-step summaries without shell command noise

#### Scenario: Verbose output
- **WHEN** `folio check --verbose` is used
- **THEN** the CLI shows the selected backend command and backend output for each step
