## ADDED Requirements

### Requirement: Skill covers folio dev playground workflow

The bundled Folio skill SHALL teach agents how to use `folio dev` for approved design-time tweak workflows without replacing the production validation/build pipeline.

#### Scenario: Skill introduces folio dev
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill describes `folio dev` as the browser playground for tuning values declared through `folio.dsl.tweaks`
- **AND** explains that playground edits persist to `<spec_dir>/theme.toml` rather than to arbitrary Python source

#### Scenario: Skill preserves production pipeline
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill keeps `folio check`, `folio build`, `folio rasterize`, and `folio reconcile` as the authoritative production workflow
- **AND** positions `folio dev` as an optional visual tuning step before final build/rasterize verification

#### Scenario: Skill warns against editing playground output
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill instructs the agent not to hand-edit playground HTML or SVG output to apply tweak changes
- **AND** instructs it to change Python tweak declarations only when the requested value is not already declared as tweakable
