## Context

The Folio playground today is a vanilla TypeScript single-file SPA (`src/folio/playground_ui/main.ts`) bundled with esbuild and served by a stdlib `http.server` from `src/folio/services/playground_server.py`. Server payloads are produced by hand-written `serialize_playground_state()` returning `dict[str, Any]`; the SPA re-types these payloads in a hand-written `PlaygroundState` interface.

This worked while the UI fit in one file, but the boundary has two structural problems:

1. **No type contract.** Adding or renaming a field on the Python side does not break the TypeScript build. The browser silently produces `undefined` until QA or production catches it.
2. **No component layer.** The UI imperatively rewrites large sub-trees on every render (custom dropdowns, swatch + hex pair, slider + chip pair, page list). Each new feature compounds the imperative state machine; multi-pane diffs, virtual scroll, and undo would require a partial rewrite anyway.

The codebase ships as a Python wheel/sdist and `folio dev` must work for users with only Python installed. Vite, Bun, and the codegen helper are maintainer-only and cannot be runtime requirements. `pydantic` is acceptable as a small new runtime dependency: it is widely deployed, already transitively present in most Python environments, and replaces hand-written `dict[str, Any]` plumbing with a typed, JSON-schema-emitting model layer.

## Goals / Non-Goals

**Goals:**
- End-to-end type safety from the Python state model to every TypeScript component, with a single source of truth (Pydantic models on the Python side).
- A component-based UI layer that scales to richer features (diff, virtual scroll, undo) without another rewrite.
- Identical wire contract for installed users: same URL paths, same JSON field names and shapes, same packaged-asset model.
- Same maintainer ergonomics: `bun run build:playground` produces the bundle, `manifest.json` tracks source hashes, asset-staleness checks still fire.
- One new small runtime dependency (`pydantic>=2.0`); no other new runtime requirements.

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

The current playground state uses dataclasses converted to dicts in `serialize_playground_state()`. We replace those dataclasses with Pydantic v2 `BaseModel` classes inside `src/folio/services/playground.py` and let `model_dump(mode="json", by_alias=True)` produce the wire payload. This:

- Makes the JSON shape declarative and inspectable.
- Gives us a JSON Schema for free via `model_json_schema()`.
- Lets us run a small codegen helper at build time to emit `src/folio/playground_ui/api.generated.ts`.

**Wire-shape preservation requirements** (these are non-negotiable to keep tests and the existing TypeScript consumer working):

- Field aliases convert snake_case Python names to the existing camelCase JSON keys: `spec_path → specPath`, `values_path → valuesPath`, `page_number → pageNumber`, `page_id → pageId`, `css_var → cssVar`.
- All currently emitted keys with `null` values must continue to be emitted. `Diagnostic.key` is `str | None` and currently appears as `"key": null` in JSON; that stays.
- Optional fields like `label`, `min`, `max`, `options` continue to appear in every emitted tweak with `null`/`[]`/value as today.
- The handler still passes the dumped dict through `json.dumps(..., sort_keys=True)` so existing snapshot ordering holds.
- Both accepted PATCH request shapes (`{"updates": {...}}` and `{"key": ..., "value": ...}`) keep working; either by parsing them into a Pydantic discriminated-union request model, or by keeping the existing accept-both parser and modeling only the response side. Default plan: model both as `TweakUpdateRequest` so the generated TypeScript covers request payloads too.

**Alternatives considered:**
- *`TypedDict` + manual export*: fewer dependencies but no JSON Schema, no validation, and the codegen step would be hand-rolled.
- *`msgspec`*: faster than Pydantic but less mainstream and weaker codegen ecosystem.
- *Pydantic at build time only*: would force us to keep the dataclass + dict serializer at runtime and rederive JSON Schema by hand from dataclasses; gives up the main benefit of Pydantic for marginal savings.

`pydantic>=2.0` is added to the project's runtime dependencies. This is a small, established library already transitively present in most Python deployments and is justified by replacing hand-rolled serialization.

### 4. Codegen step lives in `bun run build:playground`

The build script becomes a small orchestrator:

1. Run a Python helper (`uv run python -m folio._dev.gen_playground_types` or equivalent) that imports the Pydantic models, builds the JSON Schema, and emits `src/folio/playground_ui/api.generated.ts`.
2. Run `vite build --mode production` to bundle the Solid app into `src/folio/services/playground_assets/playground.{js,css}` plus `index.html`.
3. Copy `index.html` into the asset directory (Vite handles this) and update `manifest.json` source-hashes to include all new source files.

The build is reproducible and fails loudly if Python or Bun is missing. The codegen step:
- Generates types for `PlaygroundState`, `PlaygroundTweak`, `PlaygroundPage`, `Diagnostic`, and `TweakUpdateRequest`.
- Produces deterministic output across platforms (LF line endings, sorted unions, stable property order matching the Pydantic model declaration order).
- Emits a leading `// AUTO-GENERATED — do not edit. Run \`bun run build:playground\`.` comment so contributors can not mistake it for hand-written code.

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

- **Bundle size growth** → Solid plus the component split is expected to land under 50 KB minified. We add a pytest assertion (in `tests/test_playground_server.py` or a sibling test) that the served `assets/playground.js` byte size stays under 80 KB. If this trips, we investigate before merging.
- **Pydantic field-alias drift** → The codegen-drift test plus the existing `test_get_api_state_returns_pages_tweaks_values_and_diagnostics`-style assertions catch any silent rename. We additionally assert one snapshot of full `model_dump(by_alias=True)` against the legacy `serialize_playground_state` output during step 1 to prove byte-equivalence.
- **Codegen drift between dev and committed file** → The codegen test described above makes drift a hard test failure rather than a silent skew. Maintainers run `bun run build:playground` before commit; the hatch_build.py custom hook already enforces that for sdists.
- **Pydantic adds a runtime dependency** → `pydantic` is small, well-maintained, already common in the Python ecosystem, and the playground is the only place using it for now. We treat it as worth the trade.
- **Solid is less mainstream than React** → For a self-contained ~1500-line app this does not matter. Solid's API is small, well-documented, and the migration is contained in one repo subtree.
- **Vite has a slower cold start than esbuild for tiny bundles** → True but irrelevant: the build runs once per release; dev users don't run it.

## Migration Plan

The migration is staged so each commit either keeps the existing UI fully working or replaces it atomically with the Solid equivalent. No commit is allowed to land a broken intermediate UI.

1. **Pydantic models, no UI changes.** Convert `playground.py` dataclasses to Pydantic v2 models with the field aliases listed above; route serialization through `model_dump(mode="json", by_alias=True)`. Existing tests must pass without any modification.
2. **Codegen + types module, vanilla UI keeps working.** Add the gen helper, wire it into `build.mjs`, commit the first `api.generated.ts`, and switch the existing `main.ts` to import types from the generated module. The UI is still vanilla TS but now imports its types from a generated source of truth. Add the codegen-drift test.
3. **Refresh JS-substring tests in `tests/test_playground_server.py`** so they assert intent-level markers that are stable across the upcoming Solid rewrite (e.g. `"PlaygroundState"`, `'PATCH'`, `'/api/tweaks'`, `'cssVar'`). Land this before any Solid scaffold commit so step 4 does not break tests.
4. **Atomic Solid + Vite cutover.** In a single commit: add Vite, `solid-js`, `vite-plugin-solid` to `devDependencies`; replace `main.ts` with `main.tsx` and the full set of components; update `build.mjs` to invoke Vite; rebuild assets; update `manifest.json` source-hash list. After this commit `folio dev` must render with full feature parity. There is no "placeholder `<App />`" intermediate commit.
5. **Cleanup.** Remove dead vanilla-TS code paths, run the full test suite, smoke-test `folio dev` against the starter project, verify the wheel.

If at any stage tests, behavior, or bundle size regress, we revert the most recent commit; earlier stages stay intact and shippable.

## Open Questions

- *Which Python codegen tool to use?* Default plan: a tiny in-tree helper that walks `model_json_schema()` and emits TypeScript directly. Adopting `datamodel-code-generator` is heavier but more battle-tested. Decide during step 2 — choose the in-tree helper if the Pydantic models stay under ~5 types (they currently do).
- *Where does the codegen helper live?* `src/folio/_dev/gen_playground_types.py`. Hatch's current `wheel` and `sdist` configs do not exclude this path; we add explicit `src/folio/_dev/**` and `src/folio/_dev/*` patterns to both `tool.hatch.build.targets.wheel.exclude` and `tool.hatch.build.targets.sdist.exclude`. Verified by inspecting a built wheel after step 2.
