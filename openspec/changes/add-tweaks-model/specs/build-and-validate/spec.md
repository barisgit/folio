## ADDED Requirements

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
