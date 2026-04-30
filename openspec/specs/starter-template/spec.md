# Capability: Starter Template

## Purpose

Describe how Folio scaffolds a new self-contained document project from the built-in starter template.

## Requirements

### Requirement: Safe target creation
Folio SHALL scaffold starter projects only into a new or empty directory.

#### Scenario: Existing non-directory target
- **WHEN** the target path already exists and is not a directory
- **THEN** Folio rejects the create command

#### Scenario: Existing non-empty directory
- **WHEN** the target directory already exists and contains files
- **THEN** Folio rejects the create command instead of partially overwriting it

### Requirement: Template variables
Folio SHALL accept repeated `--var key=value` arguments and provide a default project slug.

#### Scenario: Valid template variables
- **WHEN** a user provides one or more `--var key=value` options
- **THEN** Folio exposes those values to the starter template during rendering

#### Scenario: Invalid variable syntax
- **WHEN** a `--var` argument does not contain `=`
- **THEN** Folio rejects the command with an error

#### Scenario: Default project slug
- **WHEN** the user does not provide `project_slug`
- **THEN** Folio derives a PyPA-safe slug from the target directory name
- **AND** falls back to `my-folio-project` if no usable slug can be derived

### Requirement: Jinja rendering behavior
Folio SHALL render template-marked file contents, render starter file names through Jinja, and copy non-template file contents verbatim.

#### Scenario: Template-marked files
- **WHEN** a starter file ends in `.j2`, `.jinja`, or `.jinja2`
- **THEN** Folio renders both the file name and file contents through Jinja
- **AND** strips the template suffix in the output file name

#### Scenario: Strict undefined variables
- **WHEN** a Jinja template references a missing variable
- **THEN** Folio fails the create command rather than silently filling in an empty value

#### Scenario: Ignored template metadata
- **WHEN** the starter contains internal metadata files such as `template.yaml`
- **THEN** Folio does not copy them into the generated project

### Requirement: Starter project structure
Folio SHALL scaffold a complete self-contained project that is ready for local authoring and agent-assisted editing.

#### Scenario: Default starter output
- **WHEN** `folio create <target>` succeeds
- **THEN** the generated project includes at least `build.py`, `pages.py`, `layout.py`, `theme.py`, `content.py`, `README.md`, `pyproject.toml`, `.gitignore`, and an `assets/` directory

#### Scenario: Buildable starter
- **WHEN** a user runs `folio build <generated-project>` against the default starter output
- **THEN** the project builds successfully end-to-end and produces rendered page SVGs in the project's `out/` directory

#### Scenario: Skill installed at project scope by default
- **WHEN** `folio create <target>` succeeds without `--no-skill`
- **THEN** the generated project contains the Folio skill installed at `<target>/.agents/skills/folio/`
- **AND** the installed skill is byte-equivalent to the bundled skill shipped inside the Folio package

#### Scenario: Skill opt-out
- **WHEN** a user runs `folio create <target> --no-skill`
- **THEN** the generated project does not contain a `.agents/skills/folio` directory
- **AND** the rest of the starter output is unaffected

### Requirement: Starter tweak scaffold

Folio SHALL scaffold starter projects with a minimal, working example of design-time tweaks.

#### Scenario: Starter includes tweak values file
- **WHEN** `folio create <target>` succeeds without opting out of normal starter files
- **THEN** the generated project includes a `theme.toml` values file beside `build.py`
- **AND** that file contains valid persisted values for the starter's declared tweaks

#### Scenario: Starter declares tweakable theme values
- **WHEN** a user inspects the generated starter `theme.py`
- **THEN** it declares at least one tweak group using `folio.dsl.tweaks`
- **AND** the declarations cover at least a brand color and a text size used by rendered starter pages

#### Scenario: Starter remains buildable
- **WHEN** a user runs `folio build <generated-project>` against the default starter output
- **THEN** the project builds successfully end-to-end using the values in `theme.toml`
- **AND** produces rendered artifacts in the project's `out/` directory

### Requirement: Starter tokens vs tweaks separation

Folio SHALL keep tweakable starter values declared as tweaks and non-tweakable starter values declared as tokens, without dual-homing the same value in both.

#### Scenario: Tweakable values are not in tokens
- **WHEN** a user inspects the generated starter `theme.py`
- **THEN** any value declared as a tweak (such as the starter brand color or hero text size) is not also declared as a token via `tokens.extend(...)`

#### Scenario: Non-tweakable named values stay in tokens
- **WHEN** a user inspects the generated starter `theme.py`
- **THEN** named colors and other constants that the starter does not expose as tweakable remain declared via `tokens.extend(...)`

### Requirement: Starter documentation for tweaks

Folio SHALL explain the tweak workflow in generated starter documentation.

#### Scenario: README documents theme.toml
- **WHEN** `folio create <target>` succeeds
- **THEN** the generated `README.md` explains that approved design values are declared as tweaks in Python and that their values live in `theme.toml`

#### Scenario: README ties production pipeline to concrete values
- **WHEN** a user reads the generated starter `README.md`
- **THEN** it explains that `folio check`, `folio build`, and `folio rasterize` produce artifacts with concrete resolved tweak values
- **AND** does not require a browser playground for production verification

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
