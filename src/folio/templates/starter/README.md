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
