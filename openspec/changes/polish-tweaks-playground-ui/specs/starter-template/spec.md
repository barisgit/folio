## ADDED Requirements

### Requirement: Starter documentation for polished playground UI

Folio SHALL describe the polished `folio dev` playground in generated starter documentation without implying that starter users need frontend tooling.

#### Scenario: README describes document workspace
- **WHEN** `folio create <target>` succeeds
- **THEN** the generated `README.md` describes `folio dev` as a browser playground with rendered page previews, page navigation, zoom controls, and tweak controls for approved values
- **AND** includes a command example for launching the playground against the generated project

#### Scenario: README says Node is not required for starter use
- **WHEN** a user reads the generated starter `README.md`
- **THEN** it explains that running `folio dev` in the generated project uses Folio's packaged playground UI
- **AND** does not instruct the user to install Node, npm, or rebuild playground frontend assets to tune `theme.toml`

#### Scenario: README preserves production workflow
- **WHEN** a user reads the generated starter `README.md`
- **THEN** it keeps `folio check`, `folio build`, and export/rasterize commands as the production verification and artifact workflow
- **AND** positions `folio dev` as an optional visual tuning step before production build verification
