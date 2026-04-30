## ADDED Requirements

### Requirement: Starter tweak scaffold

Folio SHALL scaffold starter projects with a minimal, working example of design-time tweaks.

#### Scenario: Starter includes tweak values file
- **WHEN** `folio create <target>` succeeds without opting out of normal starter files
- **THEN** the generated project includes a `theme.toml` values file beside `build.py`
- **AND** that file contains valid persisted values for the starter's declared tweaks

#### Scenario: Starter declares tweakable theme values
- **WHEN** a user inspects the generated starter `theme.py`
- **THEN** it declares at least one tweak group using `folio.dsl.tweaks`
- **AND** the declarations cover at least a brand color and a text size used by rendered starter pages

#### Scenario: Starter remains buildable
- **WHEN** a user runs `folio build <generated-project>` against the default starter output
- **THEN** the project builds successfully end-to-end using the values in `theme.toml`
- **AND** produces rendered artifacts in the project's `out/` directory

### Requirement: Starter tokens vs tweaks separation

Folio SHALL keep tweakable starter values declared as tweaks and non-tweakable starter values declared as tokens, without dual-homing the same value in both.

#### Scenario: Tweakable values are not in tokens
- **WHEN** a user inspects the generated starter `theme.py`
- **THEN** any value declared as a tweak (such as the starter brand color or hero text size) is not also declared as a token via `tokens.extend(...)`

#### Scenario: Non-tweakable named values stay in tokens
- **WHEN** a user inspects the generated starter `theme.py`
- **THEN** named colors and other constants that the starter does not expose as tweakable remain declared via `tokens.extend(...)`

### Requirement: Starter documentation for tweaks

Folio SHALL explain the tweak workflow in generated starter documentation.

#### Scenario: README documents theme.toml
- **WHEN** `folio create <target>` succeeds
- **THEN** the generated `README.md` explains that approved design values are declared as tweaks in Python and that their values live in `theme.toml`

#### Scenario: README ties production pipeline to concrete values
- **WHEN** a user reads the generated starter `README.md`
- **THEN** it explains that `folio check`, `folio build`, and `folio rasterize` produce artifacts with concrete resolved tweak values
- **AND** does not require a browser playground for production verification
