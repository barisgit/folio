## ADDED Requirements

### Requirement: Skill covers polished playground UI workflow

The bundled Folio skill SHALL teach agents to use the polished `folio dev` playground as a packaged local design workspace while preserving the production build pipeline.

#### Scenario: Skill describes document workspace
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill describes `folio dev` as a local browser workspace with rendered pages, page navigation, zoom controls, diagnostics, and controls for declared tweaks
- **AND** explains that edits persist approved values to `<spec_dir>/theme.toml`

#### Scenario: Skill warns against runtime frontend setup
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill explains that installed Folio users do not need Node, npm, or frontend source files to run `folio dev`
- **AND** treats TypeScript/CSS playground asset rebuilding as a Folio-maintainer task, not as a project-authoring task

#### Scenario: Skill preserves production verification
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill keeps `folio check`, `folio build`, `folio rasterize`, and `folio reconcile` as the authoritative production workflow
- **AND** positions the playground as an optional visual tuning step whose output must still be verified through production commands

#### Scenario: Skill warns against editing generated playground output
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill instructs agents not to hand-edit packaged playground HTML, JavaScript, CSS, or rendered SVG previews to implement document changes
- **AND** tells agents to change tweak declarations, `theme.toml`, or authored Folio source files as appropriate instead
