## MODIFIED Requirements

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
