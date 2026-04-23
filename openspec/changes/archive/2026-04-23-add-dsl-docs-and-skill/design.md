# Design: DSL docs index, `folio docs`, and Folio skill

## Context

Folio's primary consumer is an agent. The docs system must therefore be:

- **Machine-first.** A stable JSON index is the source of truth. Human views
  (terminal, markdown) are derived at render time, never committed.
- **Generated.** Hand-written reference pages will drift. Everything that
  describes a DSL symbol must come from introspecting the DSL module itself.
- **Validated.** Every example in the index is executed as a step of
  `folio check`. Broken examples break CI.
- **Shipped with the wheel.** Agents invoking `folio docs` from an installed
  package must not rely on the repo being present.

## Decisions

### D1. JSON is the only canonical artifact

Markdown is never committed to the repo. `folio docs --format=md` exists for
ad-hoc export (e.g. piping into a hosted docs site) but the repo does not
store generated markdown files. This eliminates the drift class entirely.

### D2. Index lives at `src/folio/docs/index.json`

The index is generated into the package source tree so that the wheel and
sdist ship it via the existing `[tool.hatch.build.targets.wheel]` packages
declaration. The file is committed to git and treated as a checked-in
artifact: humans read it from the repo, wheels ship it verbatim.

### D3. Build-time guard, not build-time regeneration

The Hatch build hook does **not** overwrite `src/folio/docs/index.json`
during the build. If it did, every `pip install -e .` or local
`hatch build` would dirty the working tree and race with the committed
file.

Instead the hook is a guard: it imports `folio.docs.generate`, produces the
index in memory, and compares against `src/folio/docs/index.json`. If they
differ (modulo the `generated_at` timestamp) the build fails with a message
pointing at `python -m folio.docs.generate`. The committed file is always
the shipped file; the hook only refuses to ship a stale one.

```toml
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
```

`hatch_build.py` is a thin adapter: it runs the generator, diffs, and
raises on mismatch. No logic lives there.

Regeneration is an explicit dev action via `python -m folio.docs.generate`
(or `folio docs generate`, its alias). CI runs the same command on a clean
checkout and fails if the working tree is dirty afterwards - this is the
staleness check and it is the only place the file actually gets rewritten.

### D4. Index schema (v1)

```json
{
  "version": 1,
  "generated_at": "2026-04-23T13:15:00Z",
  "folio_version": "0.1.0",
  "symbols": [
    {
      "id": "folio.dsl.page",
      "name": "page",
      "kind": "primitive",
      "module": "folio.dsl",
      "signature": "page(*children, width_mm=None, height_mm=None, id=None)",
      "summary": "Top-level page node.",
      "description": "Markdown-capable long form...",
      "params": [
        {"name": "width_mm", "type": "float | None", "doc": "Page width in millimeters."}
      ],
      "returns": {"type": "PageNode", "doc": "A renderable page."},
      "examples": [
        {
          "code": "page(rect(0, 0, 10, 10))",
          "caption": "Minimal page.",
          "setup": null
        }
      ],
      "tags": ["layout", "root"],
      "source": "folio.dsl.builtins:42"
    }
  ]
}
```

Schema notes:

- `kind` is a closed enum: `primitive`, `defs`, `token`, `style`, `builder`,
  `helper`. Anything not classifiable falls under `helper` explicitly;
  generation fails on any other value.
- `source` is a `module.path:line` string, not a filesystem path, so it
  resolves both in the repo and from an installed wheel. Line numbers come
  from `inspect.getsourcelines` applied to the *defining* function (after
  unwrapping re-exports), not to the re-export binding.
- `module` is the publicly advertised import location (e.g. `folio.dsl`),
  not the private definition module (`folio.dsl.builtins`). Agents should
  import from what the docs tell them.
- `params[].type` and `returns.type` are string renderings of annotations.
  Not structural types - rendering is `str(typing.get_type_hints(...))`.
- `examples[].setup` is optional. When present it is Python source prepended
  to `code` during validation. When absent the example stands alone.
- `version` is an integer. Any breaking change to the schema bumps it and
  the `folio docs` reader rejects indices it does not understand.

### D5. Symbol discovery across three surfaces

The generator does not do one kind of traversal; it does three, because the
public DSL surface has three shapes:

1. **`folio.dsl.__all__`** - callables and classes re-exported at the DSL
   top level. Kind is `primitive`, `defs`, `builder`, or `helper` depending
   on the symbol category. This requires that `folio.dsl` declare
   `__all__`, which it currently does not. Adding `__all__` is part of this
   change and becomes the contract for "public symbol".
2. **`folio.dsl.tokens`** - a `SimpleNamespace` of constants, nested
   namespaces, and callables (`extend`, presets). Generator enumerates
   public attributes (no leading underscore) and classifies each as
   `token` or `helper` based on whether it is a value or a callable.
3. **`folio.dsl.tokens.STYLES`** - `TextStyle` instances that are themselves
   callable and expose `.span` / `.multiline`. Each style becomes one symbol
   of kind `style`. The callable forms (`hero(...)`, `hero.span(...)`,
   `hero.multiline(...)`) are captured as additional entries in `examples`,
   not as separate symbols.

Generation walks these three surfaces in order, deduplicates by `id`, and
fails loudly if the same `id` appears twice with different `source`
locations.

### D6. Docstring is the contract

A public symbol without a docstring is a contract violation. Generation
fails with a message pointing at the symbol's source. This pressure keeps
the DSL self-documenting; the docstring sweep in task group 2 is the
one-time cost of adopting the contract.

### D7. Example validation

Example validation runs as a new step in `folio.check.runner.run_check`,
between `validate` and `lint`. It is not a toggleable backend - `folio
check` was designed as a linear pipeline and this fits that shape directly.

Each example is executed in a fresh namespace seeded with
`from folio.dsl import *` (or the module the symbol lives under, if
different). If `example.setup` is present its source is prepended before
`example.code`. The pipeline reports any raised exception as a failure
labeled `<symbol_id>[<example_index>]`.

**Validation scope is execution, not semantics.** A passing example proves
the snippet imports, parses, and evaluates without raising. It does not
prove the output is visually correct or meets any spec. That is deliberate:
correctness belongs in tests, not doc validation.

### D8. `folio docs` command surface

- `folio docs show <symbol>` - details (default human-readable rich output).
  The `show` verb is mandatory to avoid collision with other subcommands
  or future DSL symbols named `search` / `list` / `generate`.
- `folio docs search <query>` - case-insensitive substring + tag search
  over the index. Matches on `name`, `summary`, parameter names, and tags.
- `folio docs list [--kind=...]` - enumerate. `--kind` accepts any value
  from the closed `kind` enum.
- `folio docs generate` - regenerate the committed index (dev workflow).
  Alias for `python -m folio.docs.generate`.
- All subcommands accept `--format={text,json,md}`, default `text`. `--json`
  is accepted as a shortcut for `--format=json` and they must not be mixed.

Exit codes:

- `0` - success, including empty search results (parity with
  `folio search stock`).
- `1` - user error (bad flag, unparseable argument).
- `2` - symbol not found (for `folio docs show`).
- `3` - schema version mismatch on the loaded index.

`folio search` (existing asset/stock search) is **not** renamed. `docs` is
a sibling top-level command.

### D9. Skill is thin; it delegates to `folio docs`

`SKILL.md` does **not** inline the DSL reference. It teaches workflow and
tells the agent to run `folio docs search <query>` or
`folio docs show <symbol>` whenever it needs DSL information. This means
the skill itself never needs regeneration - only the index does.

The skill also includes an explicit precheck: the agent must run
`folio --version` before assuming the CLI is available, and stop with a
user-actionable message if it is not. Skills can be installed outside the
project that contains Folio, so PATH cannot be taken for granted.

### D10. Skill install scopes

- `--scope=user` installs into `~/.claude/skills/folio/`.
- `--scope=project` installs into `<cwd>/.claude/skills/folio/`. Project
  scope is literally the current working directory - no project-root
  detection heuristic. Users who want the skill elsewhere cd first.
- `folio create` auto-installs at project scope into the scaffolded
  directory. `--no-skill` opts out.
- Install is idempotent: rewriting the same content is a no-op exit 0;
  a conflicting file (different bytes from the bundled skill) requires
  `--force` and exits 3 without it. `--force` on a conflicting
  installation upgrades in place and exits 0.

### D11. No embeddings in v1

The DSL surface is small (dozens of symbols, not thousands). Substring +
keyword + tag matching on the JSON is sufficient. We can revisit if the
surface grows by an order of magnitude.

## Non-goals

- A hosted docs website. Out of scope; the markdown export path is enough
  to build one later without further design work.
- Versioned multi-release docs. The index ships with the wheel; agents read
  the version corresponding to the installed Folio.
- Docs for private or internal modules. Only the public DSL surface.
- Auto-regenerating the skill file content. The skill is hand-authored
  prose; only the JSON index is generated.
- Semantic correctness validation of examples. See D7 - execution only.

## Risks

- **Generator bugs produce a bad index that ships in a wheel.** Mitigation:
  the build-time guard (D3) fails the build if the committed index is
  stale, and tests assert that every symbol in
  `folio.dsl.__all__` / `tokens` / `tokens.STYLES` appears in the index.
- **Example drift after a DSL refactor.** Mitigation: example validation
  runs in every `folio check` (D7) and in CI before packaging.
- **Skill file placement conflicts with a user's existing
  `~/.claude/skills/folio`.** Mitigation: `folio skill install` refuses to
  overwrite without `--force` (exit 3) and prints a conflict summary.
- **Skill ships stale references after a Folio upgrade.** Mitigation: the
  skill is intentionally version-agnostic and delegates all DSL specifics
  to `folio docs`; `folio skill install --force` upgrades an existing
  install to the version bundled with the current Folio.
- **`__all__` adoption for `folio.dsl` changes a previously-ad-hoc public
  surface.** Mitigation: initial `__all__` is derived from the current
  module-level assignments (no new exports, no removals); the change is
  codification, not scoping.
