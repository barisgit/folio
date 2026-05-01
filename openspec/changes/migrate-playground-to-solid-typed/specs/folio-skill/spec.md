## MODIFIED Requirements

### Requirement: Skill covers polished playground UI workflow

The bundled Folio skill SHALL teach agents to use the polished `folio dev` playground as a packaged local design workspace while preserving the production build pipeline, and SHALL describe the playground frontend as a component-based Solid application whose API payloads are owned by Python models.

#### Scenario: Skill describes document workspace
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill describes `folio dev` as a local browser workspace with rendered pages, page navigation, zoom controls, diagnostics, and controls for declared tweaks
- **AND** explains that edits persist approved values to `<spec_dir>/theme.toml`

#### Scenario: Skill warns against runtime frontend setup
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill explains that installed Folio users do not need Node, npm, Bun, Vite, Solid source files, or a Python types-generation helper to run `folio dev`
- **AND** treats playground frontend rebuilding as a Folio-maintainer task, not as a project-authoring task

#### Scenario: Skill preserves production verification
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill keeps `folio check`, `folio build`, `folio rasterize`, and `folio reconcile` as the authoritative production workflow
- **AND** positions the playground as an optional visual tuning step whose output must still be verified through production commands

#### Scenario: Skill warns against editing generated playground output
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill instructs agents not to hand-edit packaged playground HTML, JavaScript, CSS, the generated TypeScript API types module, or rendered SVG previews to implement document changes
- **AND** tells agents to change tweak declarations, `theme.toml`, or authored Folio source files as appropriate instead

#### Scenario: Skill describes the typed playground architecture
- **WHEN** an agent reads the bundled `SKILL.md` looking for guidance on changing the playground UI
- **THEN** the skill explains that the playground frontend is a Solid component application whose JSON payload types are generated from Python payload models
- **AND** instructs agents to update the Python models when changing the API contract and to rerun the documented build command so the generated TypeScript types module stays in sync
