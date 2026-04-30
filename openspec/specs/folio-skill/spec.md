# Capability: Folio Skill

## Purpose

Describe the bundled agent skill that teaches any agent tool the Folio workflow and the `folio skill install` command that places it into an agent-neutral skills directory. The skill is not tied to any specific agent client — clients that read from a client-specific path (such as Claude Code's `~/.claude/skills/`) can symlink the installed directory.

## Requirements

### Requirement: Bundled skill asset
Folio SHALL ship a Folio-specific agent skill inside the installed package.

#### Scenario: Canonical location inside the package
- **WHEN** Folio is installed from a wheel or sdist
- **THEN** a complete skill directory is available at `folio/skill/`
  inside the package
- **AND** it contains at least a `SKILL.md` file

#### Scenario: Skill references `folio docs`
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill instructs the agent to look up DSL symbols via
  `folio docs show <symbol>` or `folio docs search <query>` rather than
  inlining the DSL reference

#### Scenario: Skill covers canonical workflow
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill describes the standard Folio workflow of
  `folio check`, `folio build`, `folio preview`, and `folio reconcile`
  in that ordering

#### Scenario: Skill includes CLI availability precheck
- **WHEN** an agent reads the bundled `SKILL.md`
- **THEN** the skill instructs it to verify `folio` is on PATH via
  `folio --version` before relying on the CLI
- **AND** tells it to stop with a user-actionable message if the CLI is
  not available

#### Scenario: Skill is version-agnostic
- **WHEN** the bundled `SKILL.md` is authored
- **THEN** it does not hardcode signatures, DSL symbol names beyond the
  workflow commands, or constants that would go stale across Folio
  versions

### Requirement: `folio skill install` command
Folio SHALL provide a `folio skill install` command that copies the
bundled skill into an agent-neutral skills directory under
`.agents/skills/folio/`.

#### Scenario: User scope installation
- **WHEN** a user runs `folio skill install --scope=user`
- **THEN** Folio writes the skill into `~/.agents/skills/folio/`
- **AND** prints the resulting absolute path on stdout

#### Scenario: Project scope installation
- **WHEN** a user runs `folio skill install --scope=project`
- **THEN** Folio writes the skill into `<cwd>/.agents/skills/folio/`,
  where `<cwd>` is the literal current working directory with no
  project-root detection
- **AND** prints the resulting absolute path on stdout

#### Scenario: Default scope
- **WHEN** a user runs `folio skill install` without `--scope`
- **THEN** Folio defaults to project scope

#### Scenario: Idempotent write
- **WHEN** a user re-runs `folio skill install` with identical source
  and destination contents
- **THEN** Folio reports a no-op and exits with code 0

#### Scenario: Conflict without `--force`
- **WHEN** the destination already contains one or more files whose
  contents differ from the bundled skill
- **THEN** Folio exits with code 3
- **AND** prints a summary listing each conflicting path

#### Scenario: Conflict resolution with `--force`
- **WHEN** a user passes `--force` and the destination contains
  conflicting files
- **THEN** Folio overwrites the destination with the bundled skill
- **AND** exits with code 0

#### Scenario: Unreadable user home
- **WHEN** `--scope=user` is used and the user's home directory cannot
  be resolved or written to
- **THEN** Folio exits with code 1 and reports the underlying OS error

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
