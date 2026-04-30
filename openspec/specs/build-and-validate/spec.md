# Capability: Build and Validate

## Purpose

Describe how Folio validates a spec and renders authored pages into selected build artifacts and build cache state.

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
Folio SHALL render validated documents into artifacts selected by named export targets in a spec-local output directory by default, using an export pipeline plan to execute target dependencies.

#### Scenario: Default output directory
- **WHEN** a user runs `folio build` against a spec file or project directory without `--out-dir`
- **THEN** Folio writes built artifacts to `<spec_dir>/out/`
- **AND** does not redirect output to the caller's current working directory when the spec lives elsewhere

#### Scenario: Explicit output directory
- **WHEN** a user provides `--out-dir`
- **THEN** Folio writes built artifacts to that directory instead

#### Scenario: Default target build
- **WHEN** a user runs `folio build` without target arguments
- **THEN** Folio builds the document's resolved default exports and their dependencies
- **AND** validates the rendered document before writing artifacts

#### Scenario: Explicit target build
- **WHEN** a user runs `folio build 1080p` or `folio build pdf`
- **THEN** Folio builds only the requested export preset targets and the dependencies required to produce them
- **AND** reports a render error if any requested target or dependency cannot be planned

#### Scenario: All target build
- **WHEN** a user runs `folio build all`
- **THEN** Folio builds every export preset declared by the document
- **AND** writes outputs in deterministic document order, dependency order, page order, and preset declaration order

#### Scenario: Single-page build
- **WHEN** a user provides `--page <n>` while building page-scoped targets
- **THEN** Folio writes only artifacts for the matching page
- **AND** reports a render error if that page number does not exist

#### Scenario: Single-page build with document-scoped target
- **WHEN** a user provides `--page <n>` with a document-scoped target such as `pdf` or `idml`
- **THEN** Folio rejects the command
- **AND** explains that `--page` applies only to page-scoped export targets

#### Scenario: Dependency outputs are not public unless requested
- **WHEN** a user builds only a terminal target such as `pdf` that depends on a PNG preset
- **THEN** Folio produces any required dependency artifacts internally
- **AND** writes only the requested terminal target to the public output directory

#### Scenario: Explicit targets in multi-document collections
- **WHEN** a collection contains documents with different export preset names
- **THEN** an explicit target build applies to documents that declare the requested target
- **AND** skips documents that do not declare that target
- **AND** reports an unknown target error only when no document declares the requested target

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
- **THEN** Folio still writes the requested output
- **AND** skips updating the last-build cache

### Requirement: Build error reporting
Folio SHALL distinguish DSL load failures from render failures.

#### Scenario: DSL load failure
- **WHEN** the spec file is missing, not a Python file, contains syntax errors, or fails while importing
- **THEN** Folio reports a build error
- **AND** exits with status code `1`

#### Scenario: Render failure
- **WHEN** document validation, target planning, pipeline execution, or page selection fails during build
- **THEN** Folio reports a render error
- **AND** exits with status code `2`

### Requirement: Color validation guidance
Folio SHALL warn when authored SVG content uses raw hex colors outside the Folio token system.

#### Scenario: Non-token hex colors
- **WHEN** a document contains literal hex colors not represented by registered token values
- **THEN** Folio emits a validation warning encouraging token usage

### Requirement: Tweak-aware validation

Folio SHALL validate persisted tweak values as part of spec validation when a spec declares tweaks.

#### Scenario: Validate with valid tweak values
- **WHEN** a user runs `folio validate <spec>` and the spec declares tweaks with valid persisted values
- **THEN** Folio validates the spec successfully when all other document validation passes
- **AND** reports no tweak value errors

#### Scenario: Validate with invalid tweak value
- **WHEN** a user runs `folio validate <spec>` and the active values file contains a value that violates its tweak declaration
- **THEN** Folio reports a validation error naming the values file and dotted key
- **AND** exits with validation failure status

#### Scenario: Validate with unknown persisted tweak key
- **WHEN** a user runs `folio validate <spec>` and the active values file contains a key that the spec no longer declares
- **THEN** Folio emits a validation warning naming the unknown key
- **AND** continues validating the document using only declared tweak values

### Requirement: Tweak-aware build inputs

Folio SHALL treat persisted tweak values as build inputs for deterministic artifact generation and cache state.

#### Scenario: Build uses persisted value
- **WHEN** a user runs `folio build <spec>` and `theme.toml` contains a valid value for a declared tweak
- **THEN** Folio renders built artifacts using the persisted value
- **AND** does not require the Python spec to hardcode that value

#### Scenario: Build output changes after values file edit
- **WHEN** a user changes a persisted tweak value and reruns `folio build`
- **THEN** Folio renders artifacts from the new value
- **AND** refreshes the last-build cache with SVG snapshots that reflect the new value

#### Scenario: Build rejects invalid value
- **WHEN** a user runs `folio build <spec>` and the active values file contains an invalid tweak value
- **THEN** Folio reports a render/build error naming the invalid key
- **AND** does not write misleading final artifacts for that failed build

#### Scenario: Build emits warning for unknown persisted key
- **WHEN** a user runs `folio build <spec>` and the active values file contains an undeclared key
- **THEN** Folio emits a non-fatal warning naming the unknown key
- **AND** completes the build using only declared tweak values

#### Scenario: Build without tweak declarations
- **WHEN** a user runs `folio validate` or `folio build` for a spec that declares no tweaks
- **THEN** Folio preserves the existing validation and build behavior
- **AND** does not require a `theme.toml` file to exist

#### Scenario: Validate and build use the shared service helper
- **WHEN** `folio validate` or `folio build` loads and renders a spec
- **THEN** it routes spec load and render through the spec load/render service helper introduced for tweak-aware execution
- **AND** consumes the helper's returned `BuildResult` and tweak registry snapshot

### Requirement: Concrete exported tweak values

Folio SHALL render authoritative build/export artifacts with concrete resolved tweak values.

#### Scenario: SVG build output
- **WHEN** `folio build` writes page SVG artifacts for a spec that uses tweak values, including live-mode tweaks
- **THEN** the written SVG attributes contain concrete values resolved from defaults or the values file
- **AND** do not contain CSS custom property references such as `var(--folio-tweak-...)`

#### Scenario: Downstream export output
- **WHEN** a PDF, PNG, or IDML export target is built from pages that use tweak values
- **THEN** the downstream export uses the same concrete resolved values as the SVG build path
