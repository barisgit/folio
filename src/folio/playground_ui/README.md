# Folio playground UI

Maintainer-only TypeScript/CSS source for the `folio dev` browser UI.

Runtime users do not need Bun, TypeScript, or these source files. Packaged
Python installs serve compiled assets from `folio.services.playground_assets`.
Keep that runtime contract intact: do not add a Bun invocation to `folio dev`
or to normal project-authoring workflows.

## Rebuild compiled assets

Rebuild after editing this directory with:

```bash
bun install --frozen-lockfile
bun run build:playground
```

The build writes `index.html`, `playground.js`, `playground.css`, and
`manifest.json` into `src/folio/services/playground_assets/`. Commit the source
changes and the regenerated compiled assets together.

## Verify package-data inclusion

Python package builds run `hatch_build.py`, which first runs
`bun install --frozen-lockfile` and `bun run build:playground`, then checks that
the packaged asset directory contains `index.html`, `playground.js`,
`playground.css`, and `manifest.json`, and that the manifest hashes match this
source tree. Run a packaging or build check before release; if the hook reports
stale or missing playground assets, rerun:

```bash
bun run build:playground
```

At runtime, the stdlib playground server loads these compiled files with
`importlib.resources`, so the same assets must be present in wheels, sdists, and
editable installs.
