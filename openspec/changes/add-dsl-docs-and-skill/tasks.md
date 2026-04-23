# Tasks

## 1. DSL public surface contract

- [ ] 1.1 Declare `folio.dsl.__all__` listing every currently-exported
      symbol in alphabetical order (codification only, no scope change).
- [ ] 1.2 Add a unit test that asserts `folio.dsl.__all__` matches the
      module's non-underscore public names, so future additions force an
      explicit opt-in.

## 2. Docstring sweep on the public DSL

- [ ] 2.1 Audit every symbol in `folio.dsl.__all__`, `folio.dsl.tokens`,
      and `folio.dsl.tokens.STYLES`.
- [ ] 2.2 Ensure each has a one-line summary, a long description where
      useful, and at least one runnable example.
- [ ] 2.3 Tag each symbol with the closed `kind` enum (`primitive`,
      `defs`, `token`, `style`, `builder`, `helper`).

## 3. DSL doc index generator

- [ ] 3.1 Add `folio.docs` package with `generate.py` entrypoint and a
      `__main__.py` that invokes it for `python -m folio.docs.generate`.
- [ ] 3.2 Define and freeze schema v1 (dataclasses + JSON serializer).
      Serializer MUST produce stable key order and sort `symbols` by
      `id`.
- [ ] 3.3 Implement symbol discovery across the three surfaces
      (`__all__`, `tokens`, `tokens.STYLES`) with deduplication by `id`
      and a failure mode for conflicting sources.
- [ ] 3.4 Resolve each symbol's source via `inspect.getsourcefile` and
      `inspect.getsourcelines` applied to the *defining* callable, after
      unwrapping re-exports, and emit as `module.path:line`.
- [ ] 3.5 Extract signature, params, return type, summary, long
      description, examples, and tags from each symbol.
- [ ] 3.6 Fail generation with a precise error when a public symbol lacks
      a docstring.
- [ ] 3.7 Write the index to `src/folio/docs/index.json`.

## 4. Build-time guard

- [ ] 4.1 Add `hatch_build.py` at repo root that imports the generator,
      produces the index in memory, and compares against the committed
      `src/folio/docs/index.json` (ignoring only `generated_at`).
- [ ] 4.2 Wire it as a custom Hatch build hook in `pyproject.toml`.
- [ ] 4.3 Hook MUST NOT modify any file under `src/` during a build.
- [ ] 4.4 Hook failure MUST point the developer at
      `python -m folio.docs.generate`.
- [ ] 4.5 Add a pytest that builds an sdist in a tmp dir and asserts the
      bundled `folio/docs/index.json` matches the committed file.

## 5. `folio docs` command

- [ ] 5.1 Add `folio.commands.docs` with `show`, `search`, `list`, and
      `generate` subcommands wired under a `docs` Typer app.
- [ ] 5.2 Implement rich terminal rendering (signature, summary, params,
      examples, source link).
- [ ] 5.3 Implement `--format={text,json,md}` across all subcommands,
      default `text`; accept `--json` as alias for `--format=json` and
      reject conflicts with exit code 1.
- [ ] 5.4 Implement case-insensitive search over name, summary, parameter
      names, and tags.
- [ ] 5.5 Reject indices whose `version` is not 1 with exit code 3.
- [ ] 5.6 Implement `folio docs show` with exit code 2 for unknown
      symbols and a nearest-neighbor hint computed from the index.
- [ ] 5.7 Implement empty-result behavior on `folio docs search` as
      exit code 0 with a "no results" message.

## 6. Example validation in `folio check`

- [ ] 6.1 Add an `examples` step to `folio.check.runner.run_check`
      between `validate` and `lint`.
- [ ] 6.2 Execute each example in a fresh namespace seeded with public
      DSL imports; prepend `example.setup` when present.
- [ ] 6.3 Report failures as `<symbol_id>[<example_index>]` with the
      exception type and message.
- [ ] 6.4 Ensure the step appears in the existing `CheckResult` summary
      rendering without needing a new flag.

## 7. Folio skill package

- [ ] 7.1 Add `src/folio/skill/` containing the bundled `SKILL.md` and
      any supporting assets.
- [ ] 7.2 Author `SKILL.md` to teach the `check -> build -> preview ->
      reconcile` workflow, direct the agent to use `folio docs` for
      reference lookups, and include the `folio --version` precheck.
- [ ] 7.3 Keep `SKILL.md` version-agnostic (no hardcoded DSL signatures
      or constants beyond workflow commands).
- [ ] 7.4 Confirm skill assets ship with the wheel and sdist.

## 8. `folio skill install` command

- [ ] 8.1 Add `folio.commands.skill` with an `install` subcommand wired
      under a `skill` Typer app.
- [ ] 8.2 Implement `--scope=user|project`, default `project` meaning
      literal `cwd` with no project-root detection.
- [ ] 8.3 Implement idempotent writes and `--force` override with exit
      code 3 on conflict, 0 on idempotent or forced install, 1 on OS
      errors (e.g. unresolvable home directory).
- [ ] 8.4 Print the resulting absolute install path on stdout on
      success.

## 9. Starter template integration

- [ ] 9.1 Have `folio create` install the skill at project scope into
      the scaffolded target directory by default.
- [ ] 9.2 Add a `--no-skill` flag for opt-out that leaves the rest of
      the starter output unaffected.
- [ ] 9.3 Update the starter `README.md` snippet to mention the
      installed skill and how to re-install via
      `folio skill install --force`.

## 10. Specs + docs

- [ ] 10.1 On acceptance, promote the spec deltas in this change
      (`dsl-docs`, `folio-skill`, `starter-template`) into the main
      `openspec/specs/` tree.
- [ ] 10.2 Add a README section pointing to `folio docs show` and
      `folio docs search` as the DSL reference entrypoints.
