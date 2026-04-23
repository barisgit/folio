# Capability: Text Layout

## Purpose

Describe Folio's typography, inline text composition, and wrapped text behavior.

## Requirements

### Requirement: Reusable text styles
Folio SHALL provide reusable text styles that can be applied directly to text nodes, spans, multiline text, and wrapped text.

#### Scenario: Applying a text style
- **WHEN** a spec passes a `TextStyle` or uses a preset from `tokens.STYLES`
- **THEN** Folio merges the style into the rendered text attributes
- **AND** explicit keyword overrides still win over preset defaults

#### Scenario: Callable style helpers
- **WHEN** a user calls a style object directly
- **THEN** it creates a text node with that style applied

#### Scenario: Style helper methods
- **WHEN** a user calls `style.span()`, `style.multiline()`, `style.wrapped_text()`, `style.measure_text()`, or `style.measure_wrapped_text()`
- **THEN** Folio delegates to the corresponding DSL helper with that style pre-applied

### Requirement: Inline text composition
Folio SHALL support plain strings, trusted markup fragments, and nested text spans inside a text node.

#### Scenario: Styled inline emphasis
- **WHEN** a text node contains nested `tspan()` fragments with stable ids
- **THEN** Folio renders the nested spans in the SVG output
- **AND** reconcile can diff those span ids independently

#### Scenario: Trusted markup
- **WHEN** a user wraps content in `markup()`
- **THEN** Folio emits the markup without escaping it as plain text
- **AND** plain string content continues to be escaped normally

### Requirement: Text measurement
Folio SHALL expose text measurement helpers before final rendering.

#### Scenario: Measuring authored text
- **WHEN** a user calls `measure_text()`
- **THEN** Folio returns width, height, line count, and line step metrics for the authored content

#### Scenario: Measuring wrapped text
- **WHEN** a user calls `measure_wrapped_text()` with wrapping constraints
- **THEN** Folio returns the metrics for the wrapped result, including whether truncation occurred

#### Scenario: Approximate measurement model
- **WHEN** Folio measures or wraps text
- **THEN** it uses an approximate text-width model derived from font size and letter spacing rather than exact font-engine layout

### Requirement: Wrapped text layout
Folio SHALL wrap text to a target width using authored typography settings.

#### Scenario: Automatic line breaking
- **WHEN** a user calls `wrapped_text()` with a positive `width_mm`
- **THEN** Folio wraps content into multiple lines that fit within that width
- **AND** uses either the provided `line_step_mm` or a default step derived from the font size

#### Scenario: Maximum line count with ellipsis
- **WHEN** wrapped content exceeds `max_lines` and `overflow="ellipsis"`
- **THEN** Folio truncates the final visible line
- **AND** appends an ellipsis when space permits

#### Scenario: Maximum line count with clipping
- **WHEN** wrapped content exceeds `max_lines` and `overflow="clip"`
- **THEN** Folio clips the overflow without appending an ellipsis

#### Scenario: Truncation warnings
- **WHEN** wrapped text truncates content with `overflow="ellipsis"` and warnings are enabled
- **THEN** Folio raises a `TextLayoutWarning`

### Requirement: Validation of wrapping inputs
Folio SHALL reject invalid wrapping configurations.

#### Scenario: Invalid wrap options
- **WHEN** `wrapped_text()` is called with a non-positive width, non-positive line step, non-positive max line count, or an unsupported overflow mode
- **THEN** Folio raises a type error instead of silently producing invalid layout
