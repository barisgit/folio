# Capability: DSL Docs

## ADDED Requirements

### Requirement: JSON documentation index
Folio SHALL publish a generated JSON index that describes every public DSL
symbol.

#### Scenario: Canonical location inside the package
- **WHEN** Folio is installed from a wheel or sdist
- **THEN** the documentation index is available at
  `folio/docs/index.json` inside the package
- **AND** its schema version is `1`

#### Scenario: Deterministic contents
- **WHEN** the generator runs twice against an unchanged source tree
- **THEN** both runs produce byte-identical index files apart from the
  `generated_at` field, which MAY differ

#### Scenario: Missing docstring rejection
- **WHEN** a public DSL symbol lacks a docstring
- **THEN** generation fails with an error naming the symbol and its source
  location

#### Scenario: Closed `kind` enum
- **WHEN** the index serializes a symbol
- **THEN** its `kind` is one of `primitive`, `defs`, `token`, `style`,
  `builder`, `helper`
- **AND** any other value causes generation to fail

#### Scenario: Source locations are module-based
- **WHEN** the index records a symbol's source location
- **THEN** it is formatted as `module.path:line` (e.g.
  `folio.dsl.builtins:42`)
- **AND** it resolves to the defining function after unwrapping
  re-exports

#### Scenario: Public symbol coverage
- **WHEN** the generator runs
- **THEN** every name in `folio.dsl.__all__`, every public attribute of
  `folio.dsl.tokens`, and every `TextStyle` under
  `folio.dsl.tokens.STYLES` appears as a symbol in the index
- **AND** no private or underscore-prefixed attribute appears

#### Scenario: Duplicate symbol ids are a failure
- **WHEN** discovery produces two symbols with the same `id` but
  different `source`
- **THEN** generation fails with an error naming both sources

### Requirement: Build-time staleness guard
Folio SHALL prevent wheels and sdists from being built against a stale
documentation index.

#### Scenario: Fresh committed index
- **WHEN** the Folio wheel or sdist is built via Hatch against a committed
  index that matches the generator output
- **THEN** the build succeeds and the artifact contains
  `folio/docs/index.json` verbatim from the source tree

#### Scenario: Stale committed index
- **WHEN** the committed `src/folio/docs/index.json` differs from what the
  generator would produce for the current source tree
- **THEN** the build fails with an error directing the developer to run
  `python -m folio.docs.generate`

#### Scenario: Build hook does not mutate the source tree
- **WHEN** the build hook runs
- **THEN** it does not modify any file under `src/`

### Requirement: Local regeneration
Folio SHALL provide exactly one canonical command that regenerates the
committed documentation index.

#### Scenario: Module entrypoint
- **WHEN** a developer runs `python -m folio.docs.generate`
- **THEN** `src/folio/docs/index.json` is rewritten from the current
  source tree

#### Scenario: CLI alias
- **WHEN** a developer runs `folio docs generate`
- **THEN** the effect is identical to `python -m folio.docs.generate`

#### Scenario: CI staleness check
- **WHEN** CI runs the regeneration command against a clean checkout
- **THEN** the working tree is unchanged on success
- **AND** CI fails if the regeneration produces a diff

### Requirement: Example validation
Folio SHALL validate every example in the index as a step of
`folio check`.

#### Scenario: Default check run validates examples
- **WHEN** a user runs `folio check`
- **THEN** the pipeline includes an `examples` step that executes every
  example in the index
- **AND** reports failures labeled `<symbol_id>[<example_index>]`

#### Scenario: Example execution context
- **WHEN** an example is validated
- **THEN** it is executed in a fresh namespace seeded with the public DSL
  imports
- **AND** if the example defines `setup`, that setup source is prepended
  to the example code before execution

#### Scenario: Scope of validation
- **WHEN** an example executes without raising
- **THEN** it is considered valid
- **AND** Folio does not assert anything about the rendered output

### Requirement: `folio docs` command surface
Folio SHALL provide a `folio docs` command group backed by the JSON index.

#### Scenario: Symbol lookup
- **WHEN** a user runs `folio docs show <symbol>`
- **THEN** Folio prints the signature, summary, long description,
  parameters, examples, and source location for that symbol
- **AND** exits with code 0 on success

#### Scenario: Unknown symbol
- **WHEN** a user runs `folio docs show` for a symbol that is not in the
  index
- **THEN** Folio exits with code 2
- **AND** prints a nearest-neighbor suggestion computed from the index

#### Scenario: Search
- **WHEN** a user runs `folio docs search <query>`
- **THEN** Folio returns symbols whose name, summary, parameter names, or
  tags match the query case-insensitively

#### Scenario: Empty search results
- **WHEN** `folio docs search <query>` matches no symbols
- **THEN** Folio exits with code 0 and reports that no results were found

#### Scenario: Listing with kind filter
- **WHEN** a user runs `folio docs list --kind=<kind>`
- **THEN** Folio lists every symbol of that kind and no others
- **AND** rejects any value that is not in the closed `kind` enum

#### Scenario: Format selection
- **WHEN** a user passes `--format=json`, `--format=md`, or `--format=text`
  to any `folio docs` subcommand
- **THEN** Folio emits output rendered in the selected format
- **AND** defaults to `text` when the flag is omitted
- **AND** accepts `--json` as a shortcut for `--format=json`

#### Scenario: Conflicting format flags
- **WHEN** a user combines `--json` with `--format=md` or any other
  non-`json` format
- **THEN** Folio exits with code 1 and reports the conflict

#### Scenario: Schema version mismatch
- **WHEN** `folio docs` loads an index whose `version` is not `1`
- **THEN** Folio exits with code 3 and refuses to operate

### Requirement: Packaged index freshness
Folio SHALL verify that the installed package's index is usable at
runtime.

#### Scenario: Installed package reports version
- **WHEN** a user runs `folio docs list --format=json` from an installed
  Folio
- **THEN** the response includes `version: 1` and a non-empty `symbols`
  array

#### Scenario: Index corruption
- **WHEN** the packaged index file is missing or not parseable as JSON
- **THEN** `folio docs` exits with code 3 and reports the problem
