# Capability: Folio Skill

## ADDED Requirements

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
bundled skill into a Claude Code skills directory.

#### Scenario: User scope installation
- **WHEN** a user runs `folio skill install --scope=user`
- **THEN** Folio writes the skill into `~/.claude/skills/folio/`
- **AND** prints the resulting absolute path on stdout

#### Scenario: Project scope installation
- **WHEN** a user runs `folio skill install --scope=project`
- **THEN** Folio writes the skill into `<cwd>/.claude/skills/folio/`,
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
