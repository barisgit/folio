# Add DSL docs index, `folio docs` command, and Folio skill

## Why

Folio is expected to be used primarily by agents. Today the only authoritative
reference for the DSL is the source code and the README. An agent that wants to
know how `path_builder` works, which styles are registered under
`tokens.STYLES`, or what keyword arguments `page()` accepts has to read the
module. That is slow, error-prone, and incompatible with the reconcile /
feedback loop we want agents to run in.

At the same time, the Folio workflow (`folio check` -> `folio build` ->
`folio preview` -> `folio reconcile`) is non-obvious for a general-purpose
agent. Even with perfect DSL docs, an agent without a Folio-specific skill
will make poor sequencing decisions (build without check, reconcile without
preview, regenerate templates instead of editing).

This change delivers three tightly coupled things:

1. **A JSON documentation index** generated from the DSL source, shipped inside
   the Folio wheel, and regenerated in CI and via a local dev script.
2. **A `folio docs` command** that reads the index and serves terminal,
   JSON, and markdown views - so both humans and agents consume the same
   source of truth.
3. **A bundled Folio skill** that teaches agents the workflow and points them
   at `folio docs` for DSL lookups. It can be installed into user or project
   scope (`folio skill install`) and is scaffolded into new projects created
   via `folio create`.

## What Changes

- **NEW capability `dsl-docs`**: JSON index schema, generator, build-time
  integration, `folio docs` command surface.
- **NEW capability `folio-skill`**: bundled skill asset, `folio skill install`
  command, scope semantics.
- **MODIFIED `starter-template`**: `folio create` installs the skill at
  project scope by default with a `--no-skill` opt-out.
- No changes to the DSL surface itself. Docstrings on existing public DSL
  symbols are tightened as part of the work but are not a contract change.

## Impact

- Affected packages: `folio.dsl` (docstring sweep), new `folio.docs` package,
  new `folio.skill` package, `folio.commands` (new `docs` and `skill`
  subcommands), `folio.templates.starter` (new `.claude/skills` entry).
- Affected specs: new `dsl-docs`, new `folio-skill`, modified
  `starter-template`.
- Build: `pyproject.toml` gains a Hatch build hook that acts as a
  staleness guard: if the committed `src/folio/docs/index.json` does not
  match what the generator would produce for the current source, the build
  fails with a message directing the developer at
  `python -m folio.docs.generate`. The hook does not mutate the source
  tree.
- Dev loop: `python -m folio.docs.generate` (alias: `folio docs generate`)
  is the one canonical command that rewrites the committed index.
- CI: runs the regeneration command on a clean checkout and fails if the
  working tree becomes dirty, and runs `folio check` which exercises
  example validation as a pipeline step.
- Public CLI surface grows by two command groups (`docs`, `skill`). The
  existing `folio search` command is unchanged.
