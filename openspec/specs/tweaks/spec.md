# Capability: Tweaks

## Purpose

Describe Folio design-time tweak declarations, project-local persisted values, validation, value resolution, and renderer integration for authoritative build output.

## Requirements

### Requirement: Tweak declaration model

Folio SHALL provide a typed design-time tweak declaration model that lets Python specs define which project values are user-tunable.

#### Scenario: Declaring a tweak group
- **WHEN** a spec imports `from folio.dsl import tweaks` and declares `tweaks.group("theme", primary=tweaks.color(default="#d9a64b"), hero_size_pt=tweaks.size_pt(default=58, min=32, max=76))`
- **THEN** Folio registers tweak declarations for the dotted keys `theme.primary` and `theme.hero_size_pt`
- **AND** stores each declaration's type, default value, label metadata when provided, validation constraints, and effective edit mode

#### Scenario: Tweak group returns resolved values
- **WHEN** a spec assigns the result of `tweaks.group(...)` to a variable
- **THEN** each declared member is accessible as an attribute on that result
- **AND** each member resolves to the persisted value when present and valid
- **AND** otherwise resolves to the declaration default

#### Scenario: Duplicate tweak key
- **WHEN** one spec load registers the same dotted tweak key more than once
- **THEN** Folio rejects the spec with a diagnostic naming the duplicate key

#### Scenario: Missing default value
- **WHEN** a tweak declaration omits a required default value
- **THEN** Folio rejects the declaration with a type-specific diagnostic before rendering output

### Requirement: Public tweak helpers

Folio SHALL provide a fixed initial set of public tweak helpers covering colors, sizes, opacity, letter spacing, choices, presets, and font choices.

#### Scenario: Initial helper surface
- **WHEN** a user imports `from folio.dsl import tweaks`
- **THEN** the namespace exposes at least `group`, `color`, `size_pt`, `size_mm`, `opacity`, `letter_spacing`, `stroke_width`, `choice`, `preset`, and `font_choice`
- **AND** does not expose an `image` helper in this change

#### Scenario: Color helper persistence shape
- **WHEN** `tweaks.color(default="#d9a64b")` is declared and persisted
- **THEN** the persisted value is a hex color string in lowercase canonical form
- **AND** Folio rejects values that are not valid CSS-compatible color strings

#### Scenario: Numeric helper bounds
- **WHEN** a numeric tweak helper such as `size_pt`, `size_mm`, `opacity`, `letter_spacing`, or `stroke_width` declares `min` and/or `max`
- **THEN** Folio enforces those bounds on persisted and resolved values

#### Scenario: Choice helper options
- **WHEN** `tweaks.choice(default="a", options=("a", "b", "c"))` is declared
- **THEN** Folio rejects persisted values that are not in the declared options

### Requirement: Spec-scoped tweak registry

Folio SHALL collect tweak declarations during a spec load through a context-scoped registry that does not leak declarations between specs or repeated loads.

#### Scenario: Declarations in imported theme module
- **WHEN** `build.py` imports `theme.py` and `theme.py` declares tweak groups
- **THEN** Folio records those declarations for the active spec load
- **AND** makes them available to validate/build after the spec renders

#### Scenario: Repeated spec load
- **WHEN** Folio loads the same spec multiple times in one process
- **THEN** each load starts from a clean tweak registry
- **AND** stale declarations from the previous load do not appear in the new registry snapshot

#### Scenario: Separate specs in one process
- **WHEN** Folio loads two different specs sequentially in one process
- **THEN** declarations from the first spec do not affect value resolution or diagnostics for the second spec

### Requirement: Persisted tweak values

Folio SHALL persist user-selected tweak values in a project-local TOML values file at `<spec_dir>/theme.toml`.

#### Scenario: Default values file resolution
- **WHEN** Folio loads a spec at `<spec_dir>/build.py` that declares tweaks
- **THEN** Folio resolves the default persisted values file to `<spec_dir>/theme.toml`
- **AND** loads values from that file when it exists

#### Scenario: Missing values file
- **WHEN** a spec declares tweaks and `<spec_dir>/theme.toml` does not exist
- **THEN** Folio uses declaration defaults for all declared tweak values
- **AND** validation and build still succeed when the declarations are otherwise valid

#### Scenario: TOML table mapping
- **WHEN** the values file contains `[theme] primary = "#111111"`
- **THEN** Folio maps that value to the dotted tweak key `theme.primary`
- **AND** does not require the Python spec to duplicate the persisted value

#### Scenario: No values_file override
- **WHEN** a spec declares tweaks
- **THEN** Folio resolves the persisted values file only at `<spec_dir>/theme.toml`
- **AND** does not accept a `values_file=` argument or alternative path in this change

#### Scenario: Values file write format
- **WHEN** Folio writes persisted tweak values
- **THEN** it emits a deterministic TOML file containing only strings, ints, floats, booleans, or simple arrays of those types
- **AND** groups values under TOML tables corresponding to their tweak group names
- **AND** writes keys within each table in canonical sorted order

### Requirement: Tweak value validation

Folio SHALL validate persisted tweak values against their Python declarations before using them to render authoritative output.

#### Scenario: Valid persisted value
- **WHEN** `theme.toml` contains a value that matches the declared tweak type and constraints
- **THEN** Folio uses that value in place of the declaration default

#### Scenario: Invalid persisted value type
- **WHEN** `theme.toml` contains `hero_size_pt = "large"` for a numeric size tweak
- **THEN** Folio rejects the active value
- **AND** reports the values file path, dotted key, expected value type, and invalid value

#### Scenario: Out-of-range persisted value
- **WHEN** a numeric tweak declares `min=32` and `max=76` and the values file contains `hero_size_pt = 120`
- **THEN** Folio rejects the active value
- **AND** reports the allowed range in the diagnostic

#### Scenario: Unknown persisted key
- **WHEN** the values file contains a key that is not declared by the currently loaded spec
- **THEN** Folio reports a non-fatal warning naming the unknown key
- **AND** ignores that key while resolving active tweak values

### Requirement: Tweak edit modes

Folio SHALL distinguish live-editable tweak values from rebuild-required tweak values based on the tweak class and rendering context, with the per-class default mode locked in this specification.

#### Scenario: Per-class default mode table
- **WHEN** a tweak is declared with one of the public helpers
- **THEN** Folio assigns the following class default modes unless a valid override is provided:
  - `color`: live
  - `opacity`: live
  - `letter_spacing`: live
  - `size_pt`: live for direct text/font-size attribute use, rebuild for derived/layout uses
  - `size_mm`: rebuild
  - `stroke_width`: live when used as the SVG presentation `stroke-width` attribute, otherwise rebuild
  - `choice`: rebuild
  - `preset`: rebuild
  - `font_choice`: rebuild

#### Scenario: Unsafe live override
- **WHEN** a declaration attempts to force `mode="live"` for a tweak class or context that Folio does not support live
- **THEN** Folio rejects the declaration or degrades it to rebuild mode with a diagnostic explaining the unsupported live behavior

#### Scenario: Rebuild required for derived expressions
- **WHEN** a spec derives a new value from a tweak by primitive-coercing it (for example `float(theme.hero_size_pt) + 4`) and uses the derived value
- **THEN** Folio treats that usage as rebuild-only
- **AND** does not preserve live metadata on the derived value

### Requirement: TweakValue wrappers

Folio SHALL return `TweakValue` wrappers from tweak helpers that resolve to primitives in build mode and preserve metadata when assigned to live-eligible style or element-attribute fields.

#### Scenario: Primitive coercion
- **WHEN** a `TweakValue` is coerced via `str()`, `float()`, `int()`, or `bool()` where applicable
- **THEN** the coercion returns the resolved primitive value

#### Scenario: Metadata preservation on live-eligible fields
- **WHEN** a `TweakValue` is assigned directly to a live-eligible field such as `TextStyle.font_size_pt` or an SVG presentation attribute backed by a live-mode helper
- **THEN** Folio stores the wrapper without coercing it to a primitive
- **AND** the wrapper exposes its declaration metadata and stable CSS-variable identifier

#### Scenario: CSS-variable identifier shape
- **WHEN** a `TweakValue` exposes its CSS-variable identifier
- **THEN** the identifier follows the `--folio-tweak-<dotted-key-with-dashes>` convention
- **AND** the identifier is stable across spec loads for the same dotted key

### Requirement: Spec load/render service helper

Folio SHALL provide a service-level helper that loads a spec, creates a tweak context, loads persisted values, executes and renders the collection, and returns both `BuildResult` and a tweak registry snapshot.

#### Scenario: Helper return shape
- **WHEN** the helper completes successfully
- **THEN** it returns the `BuildResult` produced by rendering
- **AND** a tweak registry snapshot containing declarations, resolved values, modes, and diagnostics

#### Scenario: Helper used by validate and build
- **WHEN** `folio validate` or `folio build` runs against a spec
- **THEN** it routes spec load and render through this helper
- **AND** does not bypass tweak loading by calling lower-level loader functions directly for the purpose of producing artifacts

### Requirement: Renderer mode flag

Folio SHALL expose a render-mode flag at the renderer interface so that build rendering and a future playground rendering can share the same renderer entry points.

#### Scenario: Build mode emits concrete values
- **WHEN** the renderer is invoked in build mode
- **THEN** all tweak-backed attributes are emitted as concrete resolved primitive values
- **AND** no `var(--folio-tweak-...)` references appear in build output

#### Scenario: Playground mode reserved
- **WHEN** the renderer is invoked in playground mode in this change
- **THEN** the renderer accepts the mode without error
- **AND** still emits concrete resolved values, since live CSS-variable emission is introduced in a later change

#### Scenario: Live-eligible attribute formatter path
- **WHEN** a live-eligible attribute is formatted in either mode
- **THEN** value formatting bypasses the existing `_mm` / `_pt` numeric normalization
- **AND** uses a dedicated formatter path that can later emit CSS variables without further changes to attribute call sites
