## Context

The Folio playground today is a vanilla TypeScript single-file SPA (`src/folio/playground_ui/main.ts`) bundled with esbuild and served by a stdlib `http.server` from `src/folio/services/playground_server.py`. Server payloads are produced by hand-written `serialize_playground_state()` returning `dict[str, Any]`; the SPA re-types these payloads in a hand-written `PlaygroundState` interface.

This worked while the UI fit in one file, but the boundary has two structural problems:

1. **No type contract.** Adding or renaming a field on the Python side does not break the TypeScript build. The browser silently produces `undefined` until QA or production catches it.
2. **No component layer.** The UI imperatively rewrites large sub-trees on every render (custom dropdowns, swatch + hex pair, slider + chip pair, page list). Each new feature compounds the imperative state machine; multi-pane diffs, virtual scroll, and undo would require a partial rewrite anyway.

The codebase ships as a Python wheel/sdist and `folio dev` must work for users with only Python installed. Vite, Bun, and Pydantic are acceptable as **maintainer** tooling but cannot be runtime requirements.

## Goals / Non-Goals

**Goals:**
- End-to-end type safety from the Python state model to every TypeScript component, with a single source of truth (Pydantic models on the Python side).
- A component-based UI layer that scales to richer features (diff, virtual scroll, undo) without another rewrite.
- Identical runtime contract for installed users: same URL paths, same JSON shape, same packaged-asset model, no new runtime dependencies.
- Same maintainer ergonomics: `bun run build:playground` produces the bundle, `manifest.json` tracks source hashes, asset-staleness checks still fire.

**Non-Goals:**
- Switching to FastAPI, ASGI, uvicorn, or any non-stdlib HTTP runtime.
- WebSockets, Server-Sent Events, or any push-based protocol.
- New product features in the playground (page sync, diff view, undo). These become tractable after this migration but are not implemented here.
- Visual redesign. The UI redesign just landed; this change preserves the current look and behavior.
- Multi-document or multi-theme support.

## Decisions

### 1. Solid over React

Solid uses fine-grained reactivity: signals trigger only the DOM nodes that depend on them, with no virtual DOM diff. Three concrete reasons this matters here:

- **SVG re-injection cost.** Each rendered page is a multi-KB SVG string injected via `innerHTML`. With React, every keystroke on a tweak control either re-runs the diff against that SVG subtree or forces us to wrap it in `dangerouslySetInnerHTML` plus careful memoization. With Solid, the SVG node is owned by a signal and only replaced when the page list signal changes.
- **Bundle size.** Solid + `solid-js/web` is ~7 kB gzipped. React + ReactDOM is ~45 kB. The playground bundle should stay small because it ships in the wheel.
- **Mental model match.** Tweaks are signals: each tweak has a value, a status, and a diagnostic. Solid's `createSignal` and `createMemo` map directly without state-management ceremony.

**Alternatives considered:**
- *React + Vite*: bigger bundle, more friction with SVG injection, no real upside for this app.
- *Lit + Vite*: web components are fine but the templating is less ergonomic and the ecosystem for typed component patterns is smaller.
- *Stay vanilla, add types only*: addresses problem 1 but not problem 2; the imperative DOM code keeps growing.

### 2. Vite over esbuild

esbuild handles a single-entry bundle fine, but Solid recommends `vite-plugin-solid` for proper JSX transform and dev ergonomics, and Vite's library mode produces a clean ES module bundle that the existing `playground_server.py` can serve with no changes. Vite still uses esbuild internally for transforms, so build times stay sub-second.

We keep `bun` as the script runner because the repo already standardizes on it and `package.json` already lists `bun@1.3.12` as `packageManager`.

**Alternatives considered:**
- *Stay on esbuild + manual JSX transform*: works but fights the Solid toolchain.
- *tsup*: thin esbuild wrapper, no Solid plugin support out of the box.

### 3. Pydantic v2 models as the contract source

The current playground state uses dataclasses converted to dicts in `serialize_playground_state()`. We replace those dataclasses with Pydantic v2 `BaseModel` classes inside `src/folio/services/playground.py` and let `model_dump(mode="json")` produce the wire payload. This:

- Makes the JSON shape declarative and inspectable.
- Gives us a JSON Schema for free via `model_json_schema()`.
- Lets us run `datamodel-code-generator` (or an equivalent) at build time to emit `src/folio/playground_ui/api.generated.ts`.

**Alternatives considered:**
- *`TypedDict` + manual export*: fewer dependencies but no JSON Schema, no validation, and the codegen step would be hand-rolled.
- *`msgspec`*: faster than Pydantic but less mainstream and weaker codegen ecosystem.

`pydantic` is added to the project's runtime dependencies because the server itself uses it for serialization. This is a small, established dependency (already pulled in transitively by many Folio peers) and we accept it.

### 4. Codegen step lives in `bun run build:playground`

The build script becomes a small orchestrator:

1. Run a Python helper (`uv run python -m folio._dev.gen_playground_types` or equivalent) that imports the Pydantic models, builds the JSON Schema, and emits `src/folio/playground_ui/api.generated.ts`.
2. Run `vite build --mode production` to bundle the Solid app into `src/folio/services/playground_assets/playground.{js,css}` plus `index.html`.
3. Copy `index.html` into the asset directory (Vite handles this) and update `manifest.json` source-hashes to include all new source files.

The build is reproducible and fails loudly if Python or Bun is missing.

**Alternatives considered:**
- *Run codegen in CI only*: makes local dev confusing; same generated file would drift between dev and CI.
- *Run codegen at server startup*: violates "no Node/Python frontend tooling at runtime."

### 5. Component layout

```
src/folio/playground_ui/
├── api.generated.ts          # PlaygroundState, PlaygroundTweak, ...
├── api.ts                    # fetch helpers, importing api.generated.ts
├── state.ts                  # createPlaygroundStore() — signals + actions
├── App.tsx                   # top-level grid + slot composition
├── components/
│   ├── Topbar.tsx
│   ├── PageCanvas.tsx        # IntersectionObserver + page sheets
│   ├── PageSelector.tsx      # custom dropdown
│   ├── ZoomSegments.tsx
│   ├── TweakPanel.tsx
│   ├── tweaks/
│   │   ├── ColorTweak.tsx
│   │   ├── SliderTweak.tsx
│   │   ├── SelectTweak.tsx
│   │   └── TextNumberTweak.tsx
│   └── Diagnostics.tsx
├── styles.css                # unchanged design tokens
├── index.html                # Vite entry
└── main.tsx                  # mounts <App /> into #folio-playground
```

`state.ts` is the only module that owns the store. Components consume signals and emit actions; no component talks to `fetch()` directly.

### 6. Test strategy

- `test_playground_server.py` assertions on JS bundle internals (e.g. `"function renderControls"` substrings) are replaced with assertions that look for stable, intent-level markers ("PlaygroundState", "PATCH"-bound URL strings, asset filenames) so component refactors don't keep breaking the test.
- A new `test_playground_types_codegen.py` asserts that the committed `api.generated.ts` matches the regenerated output for the current Pydantic models. This makes "did someone forget to rebuild?" a deterministic test failure.
- `test_playground_service.py` continues to assert the same payload shape, now produced by `model_dump`.

## Risks / Trade-offs

- **Bundle size growth** → Solid + the new component split is still expected to land under 50 KB minified. We add a CI assertion that `playground.js` stays under 80 KB. If this trips, we investigate before merging.
- **Codegen drift between dev and committed file** → The codegen test described above makes drift a hard test failure rather than a silent skew. Maintainers run `bun run build:playground` before commit; the hatch_build.py custom hook already enforces that for sdists.
- **Pydantic adds a runtime dependency** → `pydantic` is small, well-maintained, already common in the Python ecosystem, and the playground is the only place using it for now. We treat it as worth the trade.
- **Solid is less mainstream than React** → For a self-contained ~1500-line app this does not matter. Solid's API is small, well-documented, and the migration is contained in one repo subtree.
- **Vite has a slower cold start than esbuild for tiny bundles** → True but irrelevant: the build runs once per release; dev users don't run it.

## Migration Plan

The migration is staged so each commit leaves the playground working:

1. **Pydantic models, no UI changes.** Convert `playground.py` dataclasses to Pydantic models. `serialize_playground_state` now calls `model_dump(mode="json")`. All existing tests must pass.
2. **Codegen + types module.** Add the gen helper. Commit `api.generated.ts`. Update `main.ts` to import its types from the generated module instead of redeclaring them. UI is still vanilla TS but now type-safe.
3. **Vite + Solid scaffold.** Add Vite, `solid-js`, `vite-plugin-solid` to `devDependencies`. Update `build.mjs` to invoke Vite. Replace `main.ts` with `main.tsx` mounting a stub `<App />`. Verify the bundle still loads and produces the same DOM shell.
4. **Component port.** Move logic into Solid components in dependency order: store → diagnostics → tweak controls → tweak panel → page selector → page canvas → topbar → App. Each step keeps tests green.
5. **Cleanup.** Remove dead code, update manifest source list, run full test suite, smoke-test `folio dev` against the starter project.

If at any stage the bundle size, behavior, or test surface regresses unexpectedly, we roll back the most recent commit; earlier stages stay intact and shippable.

## Open Questions

- *Which Python codegen tool to use?* Default plan: a tiny in-tree helper that walks `model_json_schema()` and emits TypeScript directly. Adopting `datamodel-code-generator` is heavier but more battle-tested. Decide during step 2 — choose the in-tree helper if the Pydantic models stay under ~5 types (they currently do).
- *Where does the codegen helper live?* Suggested: `src/folio/_dev/gen_playground_types.py`, kept out of the wheel via the existing `tool.hatch.build.targets.wheel` exclude list. Confirm by inspecting the wheel after step 2.
