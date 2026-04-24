# Capability: Build and Validate

## Purpose

Describe how Folio validates a spec and renders authored pages into SVG output and build cache artifacts.

## Requirements

### Requirement: Validate command
Folio SHALL provide a validation command that loads a spec and validates its rendered document.

#### Scenario: Successful validation
- **WHEN** a user runs `folio validate <spec>` or `folio validate` in a project directory
- **THEN** Folio loads the resolved spec
- **AND** validates the rendered document before reporting success

#### Scenario: Validation failure
- **WHEN** spec loading or document validation fails
- **THEN** Folio reports a validation error
- **AND** exits with status code `1`

### Requirement: Build command
Folio SHALL render validated documents into artifacts selected by named export targets in a spec-local output directory by default.

#### Scenario: Default output directory
- **WHEN** a user runs `folio build` against a spec file or project directory without `--out-dir`
- **THEN** Folio writes built artifacts to `<spec_dir>/out/`
- **AND** does not redirect output to the caller's current working directory when the spec lives elsewhere

#### Scenario: Explicit output directory
- **WHEN** a user provides `--out-dir`
- **THEN** Folio writes built artifacts to that directory instead

#### Scenario: Default target build
- **WHEN** a user runs `folio build` without target arguments
- **THEN** Folio builds the document's resolved default exports
- **AND** validates the rendered document before writing artifacts

#### Scenario: Explicit target build
- **WHEN** a user runs `folio build 1080p` or `folio build pdf`
- **THEN** Folio builds only the requested export preset targets
- **AND** reports a render error if any requested target is unknown

#### Scenario: All target build
- **WHEN** a user runs `folio build all`
- **THEN** Folio builds every export preset declared by the document
- **AND** writes outputs in deterministic document order, page order, and preset declaration order

#### Scenario: Single-page build
- **WHEN** a user provides `--page <n>` while building page-scoped targets
- **THEN** Folio writes only artifacts for the matching page
- **AND** reports a render error if that page number does not exist

#### Scenario: Single-page build with document-scoped target
- **WHEN** a user provides `--page <n>` with a document-scoped target such as `pdf` or `idml`
- **THEN** Folio rejects the command
- **AND** explains that `--page` applies only to page-scoped export targets

### Requirement: Build caching
Folio SHALL cache the full last build beside the spec unless caching is explicitly disabled.

#### Scenario: Cached build artifacts
- **WHEN** `folio build` completes without `--no-cache`
- **THEN** Folio writes a last-build cache containing page SVG snapshots, a manifest, and a copy of the spec source
- **AND** the cache is namespaced by the resolved spec path so different spec files do not collide

#### Scenario: Single-page build with cache enabled
- **WHEN** a user builds with `--page <n>` and caching remains enabled
- **THEN** Folio limits written SVG output to the selected page
- **AND** still refreshes the last-build cache from the full rendered document rather than only the selected page

#### Scenario: Cache opt-out
- **WHEN** a user passes `--no-cache`
- **THEN** Folio still writes the requested SVG output
- **AND** skips updating the last-build cache

### Requirement: Build error reporting
Folio SHALL distinguish DSL load failures from render failures.

#### Scenario: DSL load failure
- **WHEN** the spec file is missing, not a Python file, contains syntax errors, or fails while importing
- **THEN** Folio reports a build error
- **AND** exits with status code `1`

#### Scenario: Render failure
- **WHEN** document validation or page selection fails during build
- **THEN** Folio reports a render error
- **AND** exits with status code `2`

### Requirement: Color validation guidance
Folio SHALL warn when authored SVG content uses raw hex colors outside the Folio token system.

#### Scenario: Non-token hex colors
- **WHEN** a document contains literal hex colors not represented by registered token values
- **THEN** Folio emits a validation warning encouraging token usage
