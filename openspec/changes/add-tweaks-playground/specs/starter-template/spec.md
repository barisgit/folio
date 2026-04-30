## ADDED Requirements

### Requirement: Starter README mentions folio dev

Folio SHALL include a `folio dev` example in the generated starter `README.md`.

#### Scenario: README mentions dev playground
- **WHEN** `folio create <target>` succeeds
- **THEN** the generated `README.md` includes a command example for running `folio dev`
- **AND** explains that the browser playground edits approved values in `theme.toml`

#### Scenario: README separates dev from production build
- **WHEN** a user reads the generated starter `README.md`
- **THEN** it explains that `folio dev` is for design-time tuning
- **AND** that production artifacts still come from `folio check`, `folio build`, and `folio rasterize`
