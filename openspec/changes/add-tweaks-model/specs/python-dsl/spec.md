## ADDED Requirements

### Requirement: Tweak helpers in the public DSL

Folio SHALL expose design-time tweak helpers through the public Python DSL surface.

#### Scenario: Importing tweak helpers
- **WHEN** a user imports `from folio.dsl import tweaks`
- **THEN** the imported `tweaks` namespace provides helpers for declaring tweak groups and supported tweak value types
- **AND** the namespace is available anywhere other public DSL symbols are available

#### Scenario: Implementation lives under folio.core.dsl
- **WHEN** a maintainer inspects the public DSL facade
- **THEN** the tweak implementation lives at `folio.core.dsl.tweaks`
- **AND** is re-exported from `folio.dsl.tweaks` so user-facing imports use the public path

#### Scenario: Public tweak helper documentation
- **WHEN** a tweak helper is part of the public DSL surface
- **THEN** it has a docstring and examples suitable for the generated DSL docs index

### Requirement: Tweak values in authored specs

Folio SHALL allow resolved tweak values to be used in authored specs anywhere the corresponding primitive value type is accepted.

#### Scenario: Tweak color in shape attribute
- **WHEN** a spec passes a color tweak value to `rect(..., fill=theme.primary)`
- **THEN** Folio accepts the authored element
- **AND** render/build uses the resolved color value for the SVG `fill` attribute

#### Scenario: Tweak number in text style
- **WHEN** a spec passes a numeric tweak value to `TextStyle(font_size_pt=theme.hero_size_pt)`
- **THEN** Folio accepts the authored text style
- **AND** render/build uses the resolved numeric value for the SVG `font-size` attribute

#### Scenario: Tweak value in Python expressions
- **WHEN** a spec coerces a tweak value to a primitive and derives another value from it
- **THEN** Folio uses the derived value correctly during render/build
- **AND** the derived value is treated as rebuild-required

### Requirement: TweakValue preservation on live-eligible fields

Folio SHALL accept `TweakValue` on live-eligible style and element-attribute fields without coercing it to a primitive at construction time.

#### Scenario: TextStyle preserves TweakValue for font_size_pt
- **WHEN** a spec assigns a `TweakValue` returned by `tweaks.size_pt(...)` to `TextStyle(font_size_pt=...)`
- **THEN** the resulting `TextStyle` instance stores the `TweakValue` wrapper
- **AND** does not eagerly convert it to `float`

#### Scenario: TextStyle preserves TweakValue for fill
- **WHEN** a spec assigns a `TweakValue` returned by `tweaks.color(...)` to `TextStyle(fill=...)`
- **THEN** the resulting `TextStyle` instance stores the `TweakValue` wrapper
- **AND** does not eagerly convert it to `str`

#### Scenario: Live-eligible element attributes accept TweakValue
- **WHEN** a spec passes a `TweakValue` to an element attribute that the renderer treats as live-eligible (for example `fill`, `stroke`, opacity attributes, or `letter_spacing`)
- **THEN** the element accepts the value without primitive coercion at construction
- **AND** renderer build mode resolves the value to a concrete primitive at the attribute boundary

### Requirement: Spec-scoped tweak registry visibility

Folio SHALL expose tweak declarations collected during a spec load through the spec load/render service helper without leaking declarations between specs.

#### Scenario: Declarations in imported theme module are visible
- **WHEN** `build.py` imports `theme.py` and `theme.py` declares tweak groups
- **THEN** the registry snapshot returned by the service helper contains those declarations

#### Scenario: Registry isolation across loads
- **WHEN** Folio loads two different specs sequentially in one process
- **THEN** the registry snapshot for the second spec contains only that spec's declarations
