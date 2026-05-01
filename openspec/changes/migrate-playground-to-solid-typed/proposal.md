## Why

The `folio dev` playground is now a vanilla TypeScript SPA that hand-types its API payloads against a Python `dict[str, Any]` serializer. Types drift silently whenever the server changes a field, the build pipeline cannot scale to richer UI surfaces (multi-pane diff, virtual scroll, undo), and there is no compile-time contract between Python state and the browser. We want full end-to-end type safety and a frontend foundation that supports a more ambitious workspace, while keeping `folio dev` a stdlib-only experience for installed users.

## What Changes

- Replace the hand-written `main.ts` UI with a Solid + Vite single-page app under `src/folio/playground_ui/`, keeping the same packaged-asset deployment model.
- Convert the playground server payload dataclasses (`PlaygroundState`, `PlaygroundTweak`, `PlaygroundPage`, `Diagnostic`) to Pydantic v2 models that own JSON serialization.
- Add a deterministic codegen step in `bun run build:playground` that emits a TypeScript types module from the Pydantic models so the SPA imports a generated, single-source-of-truth API contract.
- Replace the per-control imperative DOM rendering with Solid components and signal-based state, preserving every behavior covered by the current `tweaks-playground` capability (live CSS variables, debounced PATCH, rerender fallback, no build-cache writes, diagnostics, page navigation, zoom).
- Update build-asset checks, tests, and the `manifest.json` source-hash list to cover the new Solid/Vite source files and the generated types module.
- **BREAKING (maintainer-only)**: maintainers rebuilding playground assets now need Vite as a dev dependency in addition to Bun; installed users continue to need only Folio's Python runtime.
- Out of scope: WebSockets, FastAPI, server-sent events, multiple themes, collaboration, multi-user state, hot-reload of authored Python source.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `tweaks-playground`: tighten the build-pipeline requirement to a Solid + Vite frontend with a generated TypeScript types module sourced from Pydantic models, and require the playground UI to import only that generated contract for server payloads.
- `folio-skill`: update bundled agent guidance so it points to the Solid component layer for UI changes and warns that API payload shapes are owned by Pydantic models.
- `starter-template`: keep the existing wording about no Bun/Node requirement for starter users; add no new starter-template requirements.

## Impact

- Affected code: `src/folio/playground_ui/**` (full rewrite to Solid), `src/folio/playground_ui/build.mjs` (Vite bundle + types codegen), `src/folio/services/playground.py` (Pydantic models for state payloads), `src/folio/services/playground_server.py` (delegate JSON serialization to Pydantic), `src/folio/services/playground_assets/**` (regenerated bundle and manifest).
- New developer dependencies: `vite`, `solid-js`, `vite-plugin-solid`, and a Python-side codegen helper (e.g., `pydantic2ts` invoked via `uv run` or a small in-tree script). All stay in `devDependencies` / dev-only Python tooling.
- Tests: `tests/test_playground_server.py` expectations on the bundled JS string need to track the new Solid runtime; payload shape tests in `tests/test_playground_service.py` continue to assert the same fields, now produced by Pydantic.
- Runtime contract: `GET /`, `GET /api/state`, `PATCH /api/tweaks` keep their URL paths, methods, and JSON field names. No new endpoints are added.
- Packaging: wheel/sdist still contains only the compiled bundle and stdlib HTTP code; users installing Folio see no new runtime dependency.
