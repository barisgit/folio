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
Folio SHALL scaffold a complete self-contained project that is ready for local authoring.

#### Scenario: Default starter output
- **WHEN** `folio create <target>` succeeds
- **THEN** the generated project includes at least `build.py`, `pages.py`, `layout.py`, `theme.py`, `content.py`, `README.md`, `pyproject.toml`, `.gitignore`, and an `assets/` directory

#### Scenario: Buildable starter
- **WHEN** a user runs `folio build <generated-project>` against the default starter output
- **THEN** the project builds successfully end-to-end and produces rendered page SVGs in the project's `out/` directory
