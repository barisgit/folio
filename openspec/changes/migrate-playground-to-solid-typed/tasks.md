## 1. Pydantic-backed payload models

- [ ] 1.1 Convert `PlaygroundState`, `PlaygroundTweak`, `PlaygroundPage`, and `Diagnostic` in `src/folio/services/playground.py` to Pydantic v2 `BaseModel` classes with explicit JSON-serializable field types and `model_config = ConfigDict(populate_by_name=True)`.
- [ ] 1.2 Add field aliases that map snake_case Python names to the existing camelCase JSON keys: `spec_path → specPath`, `values_path → valuesPath`, `page_number → pageNumber`, `page_id → pageId`, `css_var → cssVar`. All other field names already match.
- [ ] 1.3 Add a `TweakUpdateRequest` Pydantic model that accepts both currently supported PATCH bodies (`{"updates": {...}}` and `{"key": ..., "value": ...}`) and have `_PlaygroundRequestHandler.do_PATCH` parse through it.
- [ ] 1.4 Update `serialize_playground_state` (or remove it) so the playground server uses `model_dump(mode="json", by_alias=True)` and continues to pass the result through `json.dumps(..., sort_keys=True)` so existing snapshot ordering holds.
- [ ] 1.5 Add `pydantic>=2.0,<3` to `[project].dependencies` in `pyproject.toml`.
- [ ] 1.6 Add a regression test that diffs the new `model_dump(by_alias=True)` output against a captured legacy `serialize_playground_state` JSON snapshot for representative state, asserting byte-for-byte equality.
- [ ] 1.7 Run `tests/test_playground_service.py` and `tests/test_playground_server.py`; payload-shape assertions must continue to pass without modification.

## 2. Types codegen helper

- [ ] 2.1 Add a maintainer-only Python module `src/folio/_dev/__init__.py` plus `src/folio/_dev/gen_playground_types.py` that imports the playground Pydantic models and emits `src/folio/playground_ui/api.generated.ts` with `PlaygroundState`, `PlaygroundTweak`, `PlaygroundPage`, `Diagnostic`, `TweakUpdateRequest`, and any nested types.
- [ ] 2.2 Ensure the generator produces deterministic output: leading `// AUTO-GENERATED — do not edit. Run \`bun run build:playground\`.` comment, LF line endings, stable property order matching Pydantic model declaration order, sorted union members.
- [ ] 2.3 Add explicit excludes for the helper to `pyproject.toml`: append `src/folio/_dev/**` and `src/folio/_dev/*` to both `tool.hatch.build.targets.wheel.exclude` and `tool.hatch.build.targets.sdist.exclude`.
- [ ] 2.4 Build a wheel and sdist and verify (`unzip -l dist/*.whl` and `tar tf dist/*.tar.gz`) that nothing under `src/folio/_dev/` is included.
- [ ] 2.5 Wire the codegen helper into `src/folio/playground_ui/build.mjs` so `bun run build:playground` regenerates `api.generated.ts` before the JS/CSS bundle step. Use `uv run python -m folio._dev.gen_playground_types` so the helper picks up the same Python environment as tests.
- [ ] 2.6 Add a test (`tests/test_playground_types_codegen.py`) that runs the helper in-process and asserts the committed `api.generated.ts` matches the freshly generated output character-for-character; failure message must name the rebuild command.
- [ ] 2.7 Switch the existing `main.ts` to import its API types from the generated module and delete the hand-written interfaces.
- [ ] 2.8 Update `manifest.json` source-hash list to include `api.generated.ts` and `src/folio/_dev/gen_playground_types.py` so stale-asset checks fire when either drifts.

## 3. Test surface refresh (before Solid cutover)

- [ ] 3.1 Refresh `test_packaged_js_preserves_current_ui_behavior` in `tests/test_playground_server.py` to assert intent-level markers stable across the upcoming rewrite (`'PlaygroundState'`, `'cssVar'`, `'/api/tweaks'`, `'PATCH'`, `'pageNumber'`, the `assets/playground.js` filename), removing checks on vanilla-TS function names like `renderPageSelector`, `renderControls`, `renderPreview`, `controlInputType`, `document.createElement("select")`.
- [ ] 3.2 Confirm that with these refreshed assertions the current vanilla-TS bundle still passes them; only then proceed to the Solid cutover.
- [ ] 3.3 Add a pytest assertion that the served `assets/playground.js` byte size is below 80 KB.

## 4. Vite + Solid atomic cutover

- [ ] 4.1 Add `vite`, `solid-js`, `vite-plugin-solid`, and (if needed) `typescript` to `devDependencies` in `package.json` and refresh `bun.lock`.
- [ ] 4.2 Add a Vite config (e.g. `src/folio/playground_ui/vite.config.ts`) that bundles the Solid app into `src/folio/services/playground_assets/playground.js` and `playground.css`, copies `index.html`, and produces those exact filenames so existing tests, `index.html`, and the static asset handler keep working unchanged.
- [ ] 4.3 Update `build.mjs` so the build step runs the codegen helper (step 2.5) and then Vite, and continues to populate the `manifest.json` source-hash list with the new source files (`vite.config.ts`, `main.tsx`, every component module, `App.tsx`, `state.ts`, `api.ts`).
- [ ] 4.4 Replace `main.ts` with `main.tsx` and the full set of Solid components (see group 5) in a single commit so the playground keeps full feature parity at every commit boundary; do not commit a placeholder `<App />` intermediate.

## 5. Component implementation (part of the atomic cutover commit)

- [ ] 5.1 Implement `state.ts` exporting a `createPlaygroundStore()` that owns `state`, `draftValues`, `pendingUpdates`, `selectedPageIndex`, `zoomMode`, and `globalStatus` signals plus `loadState`, `patchTweak`, and `selectPage` actions; types come exclusively from `api.generated.ts`.
- [ ] 5.2 Implement `<Diagnostics />` covering the global diagnostics list and per-control diagnostic propagation.
- [ ] 5.3 Implement the four tweak controls (`tweaks/ColorTweak.tsx`, `tweaks/SliderTweak.tsx`, `tweaks/SelectTweak.tsx`, `tweaks/TextNumberTweak.tsx`), preserving units, swatch behavior, range progress, and ARIA wiring.
- [ ] 5.4 Implement `<TweakPanel />` for inspector grouping and the no-tweaks empty state.
- [ ] 5.5 Implement `<PageSelector />` (custom dropdown) and `<ZoomSegments />` (segmented control) preserving keyboard and ARIA semantics.
- [ ] 5.6 Implement `<PageCanvas />` including IntersectionObserver-driven current-page tracking and the click-to-jump suppression window.
- [ ] 5.7 Implement `<Topbar />` (brand, spec-path chip, status dot) and assemble everything in `<App />`.
- [ ] 5.8 Delete `main.ts` and any other vanilla-TS modules superseded by the Solid components.

## 6. Post-cutover test confirmation

- [ ] 6.1 Add a small DOM smoke test (using stdlib `urllib` plus a regex check) confirming the served `index.html` references `assets/playground.js` and that the bundle includes a Solid `render(` call.
- [ ] 6.2 Confirm `tests/test_playground_server.py` traversal, no-cache, and JSON contract tests still pass without modification.
- [ ] 6.3 Confirm the bundle-size pytest assertion from task 3.3 still passes against the Solid bundle.

## 7. Documentation and skill updates

- [ ] 7.1 Update `src/folio/playground_ui/README.md` to describe the Solid + Vite + codegen workflow, list the maintainer prerequisites (Bun, Python with Pydantic), and document the single `bun run build:playground` rebuild command.
- [ ] 7.2 Update the bundled Folio agent skill so it reflects the typed-component playground architecture and warns against hand-editing `api.generated.ts` or compiled assets.
- [ ] 7.3 Update any cartography or codemap references (`src/folio/services/codemap.md`, `src/folio/playground_ui/` notes) that describe the old vanilla-TS UI.

## 8. Verification

- [ ] 8.1 Run `bun run build:playground` and confirm the regenerated assets, `api.generated.ts`, and `manifest.json` are clean (no diff against the committed files after a fresh build).
- [ ] 8.2 Run the full Python test suite (`uv run pytest`) and ensure all playground tests pass, including the bundle-size assertion and codegen-drift test.
- [ ] 8.3 Run `openspec validate migrate-playground-to-solid-typed --strict`.
- [ ] 8.4 Run `openspec validate --specs --strict` to confirm no main-spec drift.
- [ ] 8.5 Smoke-test `uv run folio dev <starter-project> --no-open` in a browser: verify multi-page scroll, page selection, zoom modes, every tweak control kind, diagnostics rendering, debounced PATCH persistence, and `theme.toml` updates on disk.
- [ ] 8.6 Inspect the built wheel and sdist to confirm `src/folio/_dev/**` is excluded, that `pydantic` is in declared runtime dependencies, and that the compiled `playground.js` / `playground.css` / `index.html` / `api.generated.ts` paths are correct in the wheel.
