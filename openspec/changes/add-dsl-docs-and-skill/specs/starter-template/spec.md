# Capability: Starter Template

## MODIFIED Requirements

### Requirement: Starter project structure
Folio SHALL scaffold a complete self-contained project that is ready for
local authoring and agent-assisted editing.

#### Scenario: Default starter output
- **WHEN** `folio create <target>` succeeds
- **THEN** the generated project includes at least `build.py`, `pages.py`,
  `layout.py`, `theme.py`, `content.py`, `README.md`, `pyproject.toml`,
  `.gitignore`, and an `assets/` directory

#### Scenario: Buildable starter
- **WHEN** a user runs `folio build <generated-project>` against the
  default starter output
- **THEN** the project builds successfully end-to-end and produces
  rendered page SVGs in the project's `out/` directory

#### Scenario: Skill installed at project scope by default
- **WHEN** `folio create <target>` succeeds without `--no-skill`
- **THEN** the generated project contains the Folio skill installed at
  `<target>/.claude/skills/folio/`
- **AND** the installed skill is byte-equivalent to the bundled skill
  shipped inside the Folio package

#### Scenario: Skill opt-out
- **WHEN** a user runs `folio create <target> --no-skill`
- **THEN** the generated project does not contain a `.claude/skills/folio`
  directory
- **AND** the rest of the starter output is unaffected
