# Folio playground UI

Maintainer-only Solid + TypeScript source for the `folio dev` browser UI.

Runtime users do not need Bun, Node, TypeScript, or these source files.
Packaged Python installs serve compiled assets from
`folio.services.playground_assets`. Keep that runtime contract intact: do not
add a Bun or Node invocation to `folio dev` or to normal project-authoring
workflows.

## Architecture

- `App.tsx` — Solid component tree (Topbar, Workspace, PageSelector, tweak
  controls).
- `state.ts` — `createPlaygroundStore()` owns all signals (state, draft
  values, pending updates, control diagnostics, selected page, zoom mode,
  global status) and the debounced PATCH driver.
- `api.ts` — thin fetch wrappers around `/api/state` and `/api/tweaks`.
- `api.generated.ts` — TypeScript interfaces for the JSON wire format,
  generated from the Pydantic models in `folio.services.playground`.
  **Do not hand-edit.** Run `bun run build:playground` to regenerate.
- `main.tsx` — entry point that mounts `<App />` into `#root`.
- `index.html` — thin HTML shell; Vite rewrites the module reference into
  the bundled `/assets/playground.js` and `/assets/playground.css`.
- `vite.config.ts` — bundles into `src/folio/services/playground_assets/`
  with the canonical filenames the Python static handler expects.
- `build.mjs` — orchestrates the codegen step, the Vite build, and the
  `manifest.json` update.

The wire format is owned by `folio.services.playground`. Pydantic v2 models
there (`PlaygroundState`, `PlaygroundTweak`, `PlaygroundPage`, `Diagnostic`,
`TweakUpdateRequest`) are the single source of truth; the codegen helper at
`src/folio/_dev/gen_playground_types.py` projects them into TypeScript so the
frontend stays in sync without hand-edited types.

## Rebuild compiled assets

Prerequisites: Bun (for `bun install`), and the project's Python venv
(populated by `uv sync`) so the codegen step can import Pydantic.

Rebuild after editing this directory with:

```bash
bun install --frozen-lockfile
bun run build:playground
```

The build:

1. Runs the Python codegen helper (`folio._dev.gen_playground_types`) to
   refresh `api.generated.ts`.
2. Invokes Vite (under `node`, not `bun` — `bun + vite` hangs silently on
   import) to bundle the Solid app.
3. Writes `index.html`, `playground.js`, `playground.css`, and
   `manifest.json` into `src/folio/services/playground_assets/`.

Commit the source changes and the regenerated compiled assets together.

## Verify package-data inclusion

Python package builds run `hatch_build.py`, which first runs
`bun install --frozen-lockfile` and `bun run build:playground`, then checks
that the packaged asset directory contains `index.html`, `playground.js`,
`playground.css`, and `manifest.json`, and that the manifest hashes match
this source tree. Run a packaging or build check before release; if the
hook reports stale or missing playground assets, rerun:

```bash
bun run build:playground
```

At runtime, the stdlib playground server loads these compiled files with
`importlib.resources`, so the same assets must be present in wheels,
sdists, and editable installs.

The `src/folio/_dev/` package (containing the codegen helper) is excluded
from wheels and sdists via `tool.hatch.build.targets.{wheel,sdist}.exclude`
in `pyproject.toml` — it is a maintainer-only tool, not a runtime
dependency.
