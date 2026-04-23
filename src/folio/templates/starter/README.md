# Folio Starter

Generated from the folio starter template.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e /path/to/folio   # until folio is published to PyPI
```

`folio check` auto-discovers the `.venv` adjacent to this project, so
`folio.dsl` imports resolve for ty without any extra config.

## Build

```bash
folio validate       # parse + DSL tree validation
folio build          # render SVGs into ./out/
folio preview        # rasterize cached last build to PNG
folio check          # validate + ruff + ty (optionally --fix / --format)
```

## Editing

- `content.py` — copy, constants, table data
- `pages.py` — page layout and composition
- `layout.py` / `theme.py` — reusable components and typography

Rendered output lands in `./out/`. The build cache lives in `./.cache/`.
Both are git-ignored.

## Agent workflow

`folio create` installs the Folio skill under `.agents/skills/folio/` by
default, so any agent tool that reads from the shared `.agents/skills/`
convention picks up the canonical
`check → build → preview → reconcile` workflow and uses
`folio docs show <symbol>` / `folio docs search <query>` for DSL
lookups.

If your agent client reads skills from a client-specific path (e.g.
Claude Code's `.claude/skills/`), symlink it:

```bash
ln -s .agents/skills/folio .claude/skills/folio
```

To re-install or upgrade the skill against the currently installed Folio
version:

```bash
folio skill install --force               # project scope (default)
folio skill install --scope=user --force  # ~/.agents/skills/folio/
```

Pass `folio create --no-skill` when scaffolding if you don't want the
skill auto-installed.
