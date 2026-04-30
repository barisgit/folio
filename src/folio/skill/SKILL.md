---
name: folio
description: Build, validate, rasterize, and reconcile SVG pages with Folio, a Python DSL for page layout. Invoke this skill whenever a task touches a Folio project (build.py / pages.py / layout.py) or mentions the folio CLI.
---

# Folio workflow skill

Folio is a Python DSL that compiles a `build.py` module into SVG pages. Work
on a Folio project follows a strict pipeline. The user owns correctness —
your job is to keep the pipeline green and to surface meaningful
diagnostics when it is not.

## Precheck: confirm the CLI is available

Before anything else:

```bash
folio --version
```

If this command is missing or errors, stop and tell the user:

> Folio is not on the PATH for this shell. Install it with
> `pip install folio` (or `uv add folio`) and re-run.

Do NOT attempt to patch around a missing CLI by synthesizing SVGs by hand
or editing spec files blindly. Every downstream step assumes the CLI is
available.

## Canonical pipeline: check → build → rasterize → reconcile

For any change to a Folio spec, run these steps in order and only proceed
when each one passes.

### 1. `folio check`

Runs `validate` → `examples` → `lint` → `typecheck`. This is the fastest
signal that the spec is wellformed and that the DSL it imports still
exists. Always run it first.

```bash
folio check           # defaults to cwd/build.py
folio check --fix     # auto-apply lint/format fixes
folio check --verbose # show selected backend and its output
```

- Exit code `0` means the pipeline passed.
- Exit code `1` means there are diagnostics to fix. Read the summary
  carefully — each line prefixed with `✗` names the failing step.
- Exit code `2` means an infrastructure problem (missing backend, etc).
  Report this to the user rather than retrying.

### 2. `folio build`

Only once `check` is clean, produce the requested export artifacts. This writes
page SVG/PNG targets and document PDF/IDML targets to the configured output
directory. Declared targets may depend on other presets, e.g.
`pdf(source="1080p")` uses the `1080p` PNG pipeline internally without requiring
a separate public PNG build.

```bash
folio build           # builds cwd/build.py default_exports
folio build 1080p pdf # builds named export targets
folio build path/to/spec.py all
```

### 3. `folio rasterize`

Rasterize the generated SVGs to PNGs for visual inspection. Show the
preview to the user rather than describing it from memory — rendered
output is often different from what the spec seems to say.

```bash
folio rasterize       # defaults to cached last-build pages
folio rasterize out/page1.svg --output out/page1.png
```

### 4. `folio reconcile`

Reconcile applies manual SVG edits back onto the spec. Use this only when
the user explicitly asks to pull changes out of an edited SVG — never
proactively, and never on top of a spec that has uncommitted edits you
made yourself.

```bash
folio reconcile out/page1.svg --spec .
```

## Looking up DSL symbols: `folio docs`

Never guess at DSL signatures or attribute names. The authoritative
reference is generated from the installed Folio version and served
through the CLI:

```bash
folio docs search text           # find primitives related to text
folio docs show page             # signature, params, examples, source
folio docs show folio.dsl.rect   # fully-qualified lookup
folio docs list --kind=token     # every design token
folio docs list --kind=style     # every preset TextStyle
folio docs show page --format=json   # machine-readable view
```

Use `search` whenever you are exploring; use `show` whenever you are
committing to use a specific symbol. If `show` prints `unknown symbol`,
the symbol does not exist at the installed Folio version — do not attempt
to import it.

`folio docs` reads a JSON index that ships inside the installed wheel, so
it works in any project folder regardless of where Folio itself lives.

## Approved design tweaks: `folio.dsl.tweaks` + `theme.toml`

Some projects expose sanctioned design knobs with `folio.dsl.tweaks` in
Python. Declarations live in the spec modules (often `theme.py`); current
values live in `theme.toml` next to `build.py`.

```python
from folio.dsl import TextStyle, tweaks

theme = tweaks.group(
    "theme",
    brand=tweaks.color(default="#d9a64b", label="Brand accent"),
    hero_size_pt=tweaks.size_pt(default=58, min=32, max=76),
)

DISPLAY = TextStyle(font_size_pt=theme.hero_size_pt, fill=theme.brand)
```

```toml
[theme]
brand = "#d9a64b"
hero_size_pt = 58
```

When a requested change matches an existing tweak, edit `theme.toml` and
then run the canonical pipeline. Change Python declarations only when the
requested value is not already declared as tweakable. Do not duplicate one
design value in both `tokens.extend(...)` and `tweaks.group(...)`: use
tweaks for sanctioned project-level knobs, and keep tokens for shared
design constants that are not meant to be tuned per project.

`folio validate` and `folio build` load `theme.toml`, validate values, and
emit concrete production artifacts. `folio check` → `folio build` →
`folio rasterize` → `folio reconcile` remains the authoritative workflow.

## Working in a Folio project directory

Folio projects are self-contained. A typical layout:

```
my-doc/
  build.py         # renders Document via folio.dsl
  pages.py         # page composition
  layout.py        # grid helpers
  theme.py         # project-level tokens / TextStyles
  theme.toml       # current values for approved tweaks, when declared
  pyproject.toml   # uses [tool.folio] for config
  .agents/skills/folio/   # this skill, if installed
```

The skill installs into an agent-neutral `.agents/skills/folio/`
directory. If your agent client reads skills from a different path
(e.g. Claude Code's `.claude/skills/folio/`), symlink it:

    ln -s .agents/skills/folio .claude/skills/folio

When editing, prefer:

- Modifying `pages.py` / `layout.py` / `theme.py` over `build.py`.
- Adding new helpers in the project's own modules rather than extending
  Folio itself.
- Running `folio check` after every edit batch, not at the end of the
  session.

## What NOT to do

- Do not hand-edit generated SVGs in `out/`. The user may accept a
  `folio reconcile` pass later, but don't anticipate that.
- Do not hand-edit built SVGs or screenshots to apply tweak changes. Edit
  `theme.toml` for existing declared tweaks, or adjust the Python
  declaration only when no approved tweak exists.
- Do not regenerate the bundled starter template. If the user wants to
  reset, they run `folio create` on a new path.
- Do not invent DSL symbols or keyword arguments. If `folio docs show`
  doesn't know about them, they don't exist in this installation.
- Do not swallow `folio check` failures. If the pipeline fails, surface
  the first failing step's output verbatim and stop.

## Reporting results

After completing a change, summarize:

1. The file(s) you edited.
2. The `folio check` exit code (and failing step, if any).
3. Whether you built and rasterized, and where the rendered output
   lives.

Keep the summary to a handful of lines. The user can ask for detail.
