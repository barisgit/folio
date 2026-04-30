## ADDED Requirements

### Requirement: Tweak DSL documentation coverage

Folio SHALL include public design-time tweak helpers in the generated DSL documentation index.

#### Scenario: Tweak namespace appears in docs
- **WHEN** the documentation generator runs after tweak helpers are added to the public DSL surface
- **THEN** the generated index includes the public `folio.dsl.tweaks` namespace or entry point
- **AND** includes public tweak helper symbols such as `group`, `color`, `size_pt`, `size_mm`, `opacity`, `letter_spacing`, `stroke_width`, `choice`, `preset`, and `font_choice`

#### Scenario: Tweak examples validate
- **WHEN** `folio check` runs the documentation examples step
- **THEN** examples for public tweak helpers execute successfully in the docs example context
- **AND** do not require an existing project-specific `theme.toml` file to pass

#### Scenario: Tweak helpers are searchable
- **WHEN** a user runs `folio docs search tweak` or searches for a supported tweak helper name
- **THEN** the matching public tweak helper symbols appear in the search results

#### Scenario: Tweak helper lookup
- **WHEN** a user runs `folio docs show` for a public tweak helper symbol
- **THEN** Folio prints the helper signature, summary, parameters, examples, and source location
