## ADDED Requirements

### Requirement: Skill covers tweak declaration model

The bundled Folio skill SHALL teach agents how to use design-time tweak declarations and the persisted `theme.toml` values file without bypassing the production validation/build pipeline.

#### Scenario: Skill introduces tweak declarations
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill describes `folio.dsl.tweaks` as the way to declare which project values are user-tunable
- **AND** explains that persisted values live in `<spec_dir>/theme.toml` and are loaded by `folio validate` and `folio build`

#### Scenario: Skill preserves production pipeline
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill keeps `folio check`, `folio build`, `folio rasterize`, and `folio reconcile` as the authoritative production workflow
- **AND** positions tweak edits as inputs to that pipeline rather than a replacement

#### Scenario: Skill warns against unsupported edits
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill instructs the agent not to hand-edit generated SVGs to apply tweak changes
- **AND** instructs it to change Python tweak declarations only when the requested value is not already declared as tweakable

#### Scenario: Skill explains tokens vs tweaks
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill explains that tweakable design values belong in `folio.dsl.tweaks` declarations
- **AND** that non-tweakable named values remain in `tokens.extend(...)` without being dual-homed in both places
